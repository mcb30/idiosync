"""User database"""

from abc import ABC, abstractmethod
from collections import UserString
from collections.abc import Iterable, MutableMapping
import itertools
import uuid
import weakref


##############################################################################
#
# User database entries


class Attribute(ABC):
    """A user database entry attribute"""

    def __init__(self, name, multi=False):
        self.name = name
        self.multi = multi

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)


class Entry(ABC):
    """A user database entry"""

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.key)

    def __str__(self):
        return str(self.key)

    db = None
    """Containing user database

    This is populated as a class attribute when the containing
    user database class is instantiated.
    """

    @property
    @abstractmethod
    def key(self):
        """Canonical lookup key"""

    @property
    @abstractmethod
    def uuid(self):
        """Permanent identifier for this entry"""
        pass

    @property
    def enabled(self):
        """User database entry is enabled"""
        return True

    @classmethod
    @abstractmethod
    def find(cls, key):
        """Look up user database entry"""
        pass

    @classmethod
    def prepare(cls):
        """Prepare for use as part of an idiosync user database"""
        pass


class User(Entry):
    """A user"""

    def __repr__(self):
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.user(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def groups(self):
        """Groups of which this user is a member"""
        pass


class Group(Entry):
    """A group"""

    def __repr__(self):
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.group(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def users(self):
        """Users who are members of this group"""
        pass


class WritableEntry(Entry):
    """A writable user database entry"""

    @property
    @abstractmethod
    def syncid(self):
        """Synchronization identifier"""
        pass

    @classmethod
    @abstractmethod
    def find_syncid(cls, syncid):
        """Look up user database entry by synchronization identifier"""
        pass

    @classmethod
    @abstractmethod
    def find_syncids(cls, syncids, invert=False):
        """Look up user database entries by synchronization identifier"""
        pass

    @classmethod
    def find_match(cls, entry):
        """Look up closest matching user database entry"""
        return cls.find(entry.key)

    @classmethod
    @abstractmethod
    def create(cls):
        """Create new user database entry"""
        pass

    @abstractmethod
    def delete(self):
        """Delete user database entry"""
        pass


class WritableUser(WritableEntry, User):
    """A writable user"""
    # pylint: disable=abstract-method
    pass


class WritableGroup(WritableEntry, Group):
    """A writable group"""
    # pylint: disable=abstract-method
    pass


##############################################################################
#
# User database synchronization state


class SyncCookie(UserString):
    """A synchronization cookie"""

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.data)


class State(MutableMapping):
    """User database synchronization state"""
    # pylint: disable=abstract-method

    KEY_LEN = 128
    """Maximum state key length"""

    KEY_COOKIE = 'cookie'
    """Synchronization cookie state key"""

    def __init__(self, db):
        self.db = db

    def prepare(self):
        """Prepare for use as part of an idiosync user database"""
        pass

    @property
    def cookie(self):
        """Synchronization cookie"""
        raw = self.get(self.KEY_COOKIE, None)
        return SyncCookie(raw) if raw is not None else None

    @cookie.setter
    def cookie(self, value):
        """Synchronization cookie"""
        self[self.KEY_COOKIE] = str(value)


##############################################################################
#
# User database


class Config(ABC):
    """A user database configuration"""

    def __init__(self, **kwargs):
        self.options = kwargs


class Database(ABC):
    """A user database"""

    def __init__(self, **kwargs):
        self.config = self.Config(**kwargs)
        # Construct User and Group classes attached to this database
        db = weakref.proxy(self)
        self.User = type(self.User.__name__, (self.User,), {'db': db})
        self.Group = type(self.Group.__name__, (self.Group,), {'db': db})

    @property
    @abstractmethod
    def Config(self):
        """Configuration class for this database"""
        pass

    @property
    @abstractmethod
    def User(self):
        """User class for this database"""
        pass

    @property
    @abstractmethod
    def Group(self):
        """Group class for this database"""

    def user(self, key):
        """Look up user"""
        return self.User.find(key)

    def group(self, key):
        """Look up group"""
        return self.Group.find(key)

    def find(self, key):
        """Look up user database entry"""
        entry = self.user(key)
        if entry is None:
            entry = self.group(key)
        return entry

    @property
    @abstractmethod
    def users(self):
        """All users"""
        pass

    @property
    @abstractmethod
    def groups(self):
        """All groups"""
        pass

    def prepare(self):
        """Prepare for use as an idiosync user database"""
        self.User.prepare()
        self.Group.prepare()


class WatchableDatabase(Database):
    """A watchable user database"""

    @abstractmethod
    def watch(self, oneshot=False):
        """Watch for database changes"""
        pass


class WritableDatabase(Database):
    """A writable user database"""

    def __init__(self, **kwargs):
        super(WritableDatabase, self).__init__(**kwargs)
        self.state = self.State(weakref.proxy(self))

    @property
    @abstractmethod
    def State(self):
        """State class for this database"""
        pass

    def find_syncids(self, syncids, invert=False):
        """Look up user database entries by synchronization identifier"""
        return itertools.chain(
            self.User.find_syncids(syncids, invert=invert),
            self.Group.find_syncids(syncids, invert=invert)
        )

    @abstractmethod
    def commit(self):
        """Commit database changes"""
        pass

    def prepare(self):
        """Prepare for use as an idiosync user database"""
        super(WritableDatabase, self).prepare()
        self.state.prepare()


##############################################################################
#
# Synchronization identifiers


class SyncId(uuid.UUID):
    """A synchronization identifier

    A synchronization identifier is a UUID used to permanently
    identify a user database entry.

    For a source user database, the requirement is that the
    synchronization identifier is an immutable property of the user
    database entry.  It is not necessary for the source database to
    support looking up an entry via its synchronization identifier.

    For example:

        An LDAP database may choose to use the entryUUID operational
        attribute as the synchronization identifier.

        A SQL database may choose to derive a synchronization
        identifier as a version 5 UUID by computing the SHA-1 hash of
        a table name and an integer primary key.  Such an identifier
        is an immutable property of the database entry (assuming that
        the integer primary key value is immutable), even though it
        cannot be used directly to look up an entry within the SQL
        database.

    For a destination user database, the externally supplied
    synchronization identifier is stored as an additional property of
    each synchronized user database entry.  The destination database
    must support looking up an entry via the externally supplied
    synchronization identifier.

    Note that a synchronization identifier does not encode any
    information about whether the user database entry represents a
    user or a group.  Destination user databases must therefore
    support looking up an entry via the externally supplied
    synchronization identifier without knowing the type of the entry
    in advance.

    Bulk deletions may be carried out efficiently using only a list of
    synchronization identifiers.
    """

    def __init__(self, *args, uuid=None, **kwargs):
        # pylint: disable=redefined-outer-name
        if uuid is not None:
            super(SyncId, self).__init__(*args, bytes=uuid.bytes, **kwargs)
        else:
            super(SyncId, self).__init__(*args, **kwargs)


class SyncIds(Iterable):
    """A list of synchronization identifiers"""

    def __init__(self, iterable):
        self.iterable = iterable

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.iterable)

    def __iter__(self):
        return iter(self.iterable)


class UnchangedSyncIds(SyncIds):
    """A list of synchronization identifiers for unchanged database entries"""
    pass


class DeletedSyncIds(SyncIds):
    """A list of synchronization identifiers for deleted database entries"""
    pass


class RefreshComplete(object):
    """An indication that the refresh stage of synchronization is complete"""

    def __init__(self, autodelete=False):
        self.autodelete = autodelete

    def __repr__(self):
        return "%s(autodelete=%r)" % (self.__class__.__name__, self.autodelete)
