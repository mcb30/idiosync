"""User database synchronization"""

from abc import ABC, abstractmethod
import logging
from .base import (Entry, User, SyncCookie, SyncId, SyncIds, UnchangedSyncIds,
                   DeletedSyncIds, RefreshComplete)

logger = logging.getLogger(__name__)


class AttributeSynchronizer:
    """A user database entry attribute synchronizer"""

    def __init__(self, name, Src, Dst):
        self.name = name
        self.Src = Src
        self.Dst = Dst
        self.sync = (
            self.sync_multi_to_multi if self.Src.multi and self.Dst.multi else
            self.sync_multi_to_single if self.Src.multi else
            self.sync_single_to_multi if self.Dst.multi else
            self.sync_single_to_single
        )

    def __repr__(self):
        return "%s(%r,%r)" % (self.__class__.__name__, self.Src, self.Dst)

    def sync_multi_to_multi(self, src, dst):
        """Synchronize multi-valued attribute to multi-valued attribute"""
        srcval = getattr(src, self.name)
        dstval = getattr(dst, self.name)
        if set(dstval) != set(srcval):
            setattr(dst, self.name, srcval)

    def sync_multi_to_single(self, src, dst):
        """Synchronize multi-valued attribute to single-valued attribute"""
        srcval = getattr(src, self.name)
        dstval = getattr(dst, self.name)
        if dstval not in srcval:
            setattr(dst, self.name, next(iter(srcval), None))

    def sync_single_to_multi(self, src, dst):
        """Synchronize single-valued attribute to multi-valued attribute"""
        srcval = getattr(src, self.name)
        dstval = getattr(dst, self.name)
        if set(dstval) != set((srcval,)):
            setattr(dst, self.name, (srcval,))

    def sync_single_to_single(self, src, dst):
        """Synchronize single-valued attribute to single-valued attribute"""
        srcval = getattr(src, self.name)
        dstval = getattr(dst, self.name)
        if dstval != srcval:
            setattr(dst, self.name, srcval)


class EntrySynchronizer(ABC):
    """A user database entry synchronizer"""

    def __init__(self, Src, Dst):

        # Record source and destination classes
        self.Src = Src
        self.Dst = Dst

        # Filter attribute list and construct attribute synchronizers
        self.attrs = [x for x in self.attrs
                      if hasattr(self.Src, x) and hasattr(self.Dst, x)]
        for attr in self.attrs:
            attrsync = AttributeSynchronizer(attr, getattr(self.Src, attr),
                                             getattr(self.Dst, attr))
            setattr(self, attr, attrsync)

    def __repr__(self):
        return "%s(%s,%s)" % (self.__class__.__name__, self.Src.__name__,
                              self.Dst.__name__)

    @property
    @abstractmethod
    def attrs(self):
        """Attribute list"""

    def sync(self, src, dst):
        """Synchronize entries"""

        # Synchronize synchronization identifier
        if dst.syncid != src.uuid:
            dst.syncid = src.uuid

        # Synchronize enabled status
        if dst.enabled != src.enabled:
            dst.enabled = src.enabled

        # Synchronize attributes
        for attr in self.attrs:
            attrsync = getattr(self, attr)
            attrsync.sync(src, dst)


class UserSynchronizer(EntrySynchronizer):
    """A user synchronizer"""

    attrs = ['commonName', 'displayName', 'employeeNumber', 'givenName',
             'initials', 'mail', 'mobile', 'surname', 'telephoneNumber',
             'title', 'uid']


class GroupSynchronizer(EntrySynchronizer):
    """A group synchronizer"""

    attrs = ['commonName', 'description']


class DatabaseSynchronizer:
    """A user database synchronizer"""

    UserSynchronizer = UserSynchronizer
    GroupSynchronizer = GroupSynchronizer

    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.user = self.UserSynchronizer(src.User, dst.User)
        self.group = self.GroupSynchronizer(src.Group, dst.Group)

    def __repr__(self):
        return "%s(%r,%r)" % (self.__class__.__name__, self.src, self.dst)

    def entry(self, src, syncids=None, strict=False):
        """Synchronize a single database entry"""

        # Construct synchronization identifier
        syncid = SyncId(uuid=src.uuid)

        # Add to list of observed synchronization identifiers
        if syncids is not None:
            syncids |= {syncid}

        # Determine type of entry
        if isinstance(src, User):
            syncer = self.user
            DstEntry = self.dst.User
        else:
            syncer = self.group
            DstEntry = self.dst.Group

        # Identify or create corresponding destination entry
        dst = DstEntry.find_syncid(syncid)
        if dst is None and not strict:
            logger.info("guessing matching entry for %s", src)
            dst = DstEntry.find_match(src)
        if dst is None:
            logger.info("creating new entry for %s", src)
            dst = DstEntry.create()

        # Synchronize entry
        logger.info("synchronizing entry %s", src)
        syncer.sync(src, dst)

    def delete(self, syncids, invert=False, delete=False):
        """Delete (or disable) multiple database entries"""
        for dst in self.dst.find_syncids(syncids, invert=invert):
            if delete:
                logger.info("deleting entry %s", dst)
                dst.delete()
            elif dst.enabled:
                logger.info("disabling entry %s", dst)
                dst.enabled = False

    def sync(self, persist=True, strict=False, delete=False):
        """Synchronize database"""

        # Prepare destination database
        self.dst.prepare()

        # Refresh database and watch for changes
        syncids = set()
        for src in self.src.watch(cookie=self.dst.state.cookie,
                                  persist=persist):
            if isinstance(src, Entry):

                # Synchronize entry
                self.entry(src, syncids=syncids, strict=strict)

                # Commit changes unless this is part of a bulk refresh
                if not syncids:
                    self.dst.commit()

            elif isinstance(src, UnchangedSyncIds):

                # Add to list of observed synchronization identifiers
                if syncids is not None:
                    syncids |= set(src)

            elif isinstance(src, DeletedSyncIds):

                # Delete synchronization identifiers
                self.delete(src, invert=False, delete=delete)

            elif isinstance(src, RefreshComplete):

                # Delete unmentioned synchronization identifiers if applicable
                if syncids is not None and src.autodelete:
                    logger.info("deleting unmentioned entries")
                    self.delete(SyncIds(syncids), invert=True, delete=delete)

                # Clear list of synchronization identifiers
                syncids = None

                # Commit changes
                logger.info("refresh complete")
                self.dst.commit()

            elif isinstance(src, SyncCookie):

                # Update stored cookie
                self.dst.state.cookie = src

                # Commit changes unless this is part of a bulk refresh
                if not syncids:
                    self.dst.commit()

            else:

                raise TypeError(src)


def synchronize(src, dst, **kwargs):
    """Synchronize source database to destination database"""
    DatabaseSynchronizer(src, dst).sync(**kwargs)
