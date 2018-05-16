"""User database synchronization"""

from abc import ABC, abstractmethod


class TooManyValuesError(TypeError):
    """Attribute has too many values"""

    def __str__(self):
        return "Attribute '%s' has too many values" % self.args


class AttributeSynchronizer(object):
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
        if len(srcval) > 1:
            raise TooManyValuesError(self.name)
        if set((dstval,)) != set(srcval):
            setattr(dst, self.name, list(srcval)[0])

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
        pass

    def sync(self, src, dst):
        """Synchronize entries"""

        # Synchronize canonical name
        if dst.name != src.name:
            dst.name = src.name

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
             'title']


class GroupSynchronizer(EntrySynchronizer):
    """A group synchronizer"""

    attrs = ['commonName', 'description']


class DatabaseSynchronizer(object):
    """A user database synchronizer"""
    # pylint: disable=too-few-public-methods

    UserSynchronizer = UserSynchronizer
    GroupSynchronizer = GroupSynchronizer

    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.user = self.UserSynchronizer(src.User, dst.User)
        self.group = self.GroupSynchronizer(src.Group, dst.Group)

    def __repr__(self):
        return "%s(%r,%r)" % (self.__class__.__name__, self.src, self.dst)
