"""User database"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
import uuid
import weakref

##############################################################################
#
# Exceptions


class NoSuchEntryError(Exception):
    """User database entry does not exist"""

    def __str__(self):
        return "No such entry: '%s'" % self.args


class NoSuchUserError(NoSuchEntryError):
    """User does not exist"""

    def __str__(self):
        return "No such user: '%s'" % self.args


class NoSuchGroupError(NoSuchEntryError):
    """Group does not exist"""

    def __str__(self):
        return "No such group: '%s'" % self.args


##############################################################################
#
# User database entries


class Attribute(ABC):
    """A user database entry attribute"""
    # pylint: disable=too-few-public-methods

    def __init__(self, name, multi=False):
        self.name = name
        self.multi = multi

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)


class Entry(ABC):
    """A user database entry"""
    # pylint: disable=too-few-public-methods

    NoSuchEntryError = NoSuchEntryError

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.key)

    def __str__(self):
        return self.name

    db = None
    """Containing user database

    This is populated as a class attribute when the containing
    user database class is instantiated.
    """

    enabled = True
    """User database entry is enabled"""

    @property
    def name(self):
        """Canonical name"""
        return self.key

    @staticmethod
    def match(other):
        """Identify matching user database entry"""
        return other.name

    @property
    @abstractmethod
    def uuid(self):
        """Permanent identifier for this entry"""
        pass

    @classmethod
    def prepare(cls):
        """Prepare for use as part of an idiosync user database"""
        pass


class User(Entry):
    """A user"""
    # pylint: disable=too-few-public-methods

    NoSuchEntryError = NoSuchUserError

    @property
    @abstractmethod
    def groups(self):
        """Groups of which this user is a member"""
        pass


class Group(Entry):
    """A group"""
    # pylint: disable=too-few-public-methods

    NoSuchEntryError = NoSuchGroupError

    @property
    @abstractmethod
    def users(self):
        """Users who are members of this group"""
        pass


##############################################################################
#
# User database


class Config(ABC):
    """A user database configuration"""
    # pylint: disable=too-few-public-methods

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
        """Fetch user"""
        if isinstance(key, User):
            key = self.User.match(key)
        return self.User(key)

    def group(self, key):
        """Fetch group"""
        if isinstance(key, Group):
            key = self.Group.match(key)
        return self.Group(key)

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

    @abstractmethod
    def commit(self):
        """Commit database changes"""
        pass


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
    # pylint: disable=too-few-public-methods

    def __init__(self, iterable):
        self.iterable = iterable

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.iterable)

    def __iter__(self):
        return iter(self.iterable)


class UnchangedSyncIds(SyncIds):
    """A list of synchronization identifiers for unchanged database entries"""
    # pylint: disable=too-few-public-methods
    pass


class DeletedSyncIds(SyncIds):
    """A list of synchronization identifiers for deleted database entries"""
    # pylint: disable=too-few-public-methods
    pass


class RefreshComplete(object):
    """An indication that the refresh stage of synchronization is complete"""
    # pylint: disable=too-few-public-methods

    def __init__(self, autodelete=False):
        self.autodelete = autodelete

    def __repr__(self):
        return "%s(autodelete=%r)" % (self.__class__.__name__, self.autodelete)
