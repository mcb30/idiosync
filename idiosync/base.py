"""User database"""

# pylint: disable=abstract-method

from abc import ABC, abstractmethod
from collections import UserString
from collections.abc import Iterable, MutableMapping
import importlib
import inspect
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

    @property
    def enabled(self):
        """User database entry is enabled"""
        return True

    @classmethod
    @abstractmethod
    def find(cls, key):
        """Look up user database entry"""

    @classmethod
    def prepare(cls):
        """Prepare for use as part of an idiosync user database"""


class User(Entry):
    """A user"""

    def __repr__(self):
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.user(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def groups(self):
        """Groups of which this user is a member"""


class Group(Entry):
    """A group"""

    def __repr__(self):
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.group(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def users(self):
        """Users who are members of this group"""


class WritableEntry(Entry):
    """A writable user database entry"""

    @property
    @abstractmethod
    def syncid(self):
        """Synchronization identifier"""

    @classmethod
    @abstractmethod
    def find_syncid(cls, syncid):
        """Look up user database entry by synchronization identifier"""

    @classmethod
    @abstractmethod
    def find_syncids(cls, syncids, invert=False):
        """Look up user database entries by synchronization identifier"""

    @classmethod
    def find_match(cls, entry):
        """Look up closest matching user database entry"""
        return cls.find(entry.key)

    @classmethod
    @abstractmethod
    def create(cls):
        """Create new user database entry"""

    @abstractmethod
    def delete(self):
        """Delete user database entry"""


class WritableUser(WritableEntry, User):
    """A writable user"""


class WritableGroup(WritableEntry, Group):
    """A writable group"""


##############################################################################
#
# User database synchronization state


class SyncCookie(UserString):
    """A synchronization cookie"""

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.data)


class State(MutableMapping):
    """User database synchronization state"""

    KEY_LEN = 128
    """Maximum state key length"""

    KEY_COOKIE = 'cookie'
    """Synchronization cookie state key"""

    def __init__(self, db):
        self.db = db

    def prepare(self):
        """Prepare for use as part of an idiosync user database"""

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

    plugins = {}
    """Registered plugins"""

    def __init__(self, **kwargs):
        self.config = self.Config(**kwargs)
        # Construct User and Group classes attached to this database
        db = weakref.proxy(self)
        self.User = type(self.User.__name__, (self.User,), {'db': db})
        self.Group = type(self.Group.__name__, (self.Group,), {'db': db})

    def __init_subclass__(cls, plugin=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if plugin is None:
            plugin = cls.__module__
        if not inspect.isabstract(cls):
            if plugin in cls.plugins:
                raise ValueError("Duplicate plugin name '%s' for %s and %s" %
                                 (plugin, cls.plugins[plugin], cls))
            cls.plugins[plugin] = cls

    @classmethod
    def plugin(cls, plugin):
        """Find database class by plugin name"""
        if '.' not in plugin:
            plugin = 'idiosync.%s' % plugin
        if plugin not in cls.plugins:
            importlib.import_module(plugin)
        if plugin not in cls.plugins:
            raise KeyError("Unknown plugin '%s'" % plugin)
        return cls.plugins[plugin]

    @property
    @abstractmethod
    def Config(self):
        """Configuration class for this database"""

    @property
    @abstractmethod
    def User(self):
        """User class for this database"""

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

    @property
    @abstractmethod
    def groups(self):
        """All groups"""

    def prepare(self):
        """Prepare for use as an idiosync user database"""
        self.User.prepare()
        self.Group.prepare()


class WatchableDatabase(Database):
    """A watchable user database"""

    @abstractmethod
    def watch(self, cookie=None, persist=True):
        """Watch for database changes"""


class WritableDatabase(Database):
    """A writable user database"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = self.State(weakref.proxy(self))

    @property
    @abstractmethod
    def State(self):
        """State class for this database"""

    def find_syncids(self, syncids, invert=False):
        """Look up user database entries by synchronization identifier"""
        return itertools.chain(
            self.User.find_syncids(syncids, invert=invert),
            self.Group.find_syncids(syncids, invert=invert)
        )

    @abstractmethod
    def commit(self):
        """Commit database changes"""

    def prepare(self):
        """Prepare for use as an idiosync user database"""
        super().prepare()
        self.state.prepare()


def database(plugin, **kwargs):
    """Construct database by plugin name"""
    return Database.plugin(plugin)(**kwargs)


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
            super().__init__(*args, bytes=uuid.bytes, **kwargs)
        else:
            super().__init__(*args, **kwargs)


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


class DeletedSyncIds(SyncIds):
    """A list of synchronization identifiers for deleted database entries"""


class RefreshComplete:
    """An indication that the refresh stage of synchronization is complete"""

    def __init__(self, autodelete=False):
        self.autodelete = autodelete

    def __repr__(self):
        return "%s(autodelete=%r)" % (self.__class__.__name__, self.autodelete)
