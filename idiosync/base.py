"""User database"""

from abc import abstractmethod
from collections import UserString
from collections.abc import Iterable, MutableMapping
from dataclasses import dataclass
import io
import itertools
import sys
from typing import ClassVar, Type
from uuid import UUID
import weakref


##############################################################################
#
# User database entries


@dataclass
class Attribute:
    """A user database entry attribute"""

    name: str = None
    multi: bool = False

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name


class Entry:
    """A user database entry"""

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.key)

    def __str__(self):
        return str(self.key)

    db: ClassVar['Database'] = None
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
    def find_syncid(cls, syncid):
        """Look up user database entry by synchronization identifier"""
        return next(cls.find_syncids({syncid}), None)

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


@dataclass  # type: ignore[misc]
class State(MutableMapping):
    """User database synchronization state"""

    db: 'Database'

    KEY_LEN: ClassVar[int] = 128
    """Maximum state key length"""

    KEY_COOKIE: ClassVar[str] = 'cookie'
    """Synchronization cookie state key"""

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
# Tracing


class TraceEvent:
    """A database trace event"""

    def __str__(self):
        with io.StringIO() as buf:
            self.write(buf)
            return buf.getvalue()

    @abstractmethod
    def write(self, fh):
        """Write trace event to output file"""

    @classmethod
    @abstractmethod
    def read(cls, fh):
        """Read trace event from input file"""

    @classmethod
    @abstractmethod
    def delimiter(cls, line):
        """Test for start-of-event delimiter in input file"""

    @classmethod
    def readall(cls, fh):
        """Read all trace events from input file"""
        delimiter = cls.delimiter
        with io.StringIO() as subfh:
            while True:
                line = fh.readline()
                if delimiter(line) or not line:
                    if subfh.tell():
                        subfh.seek(0)
                        yield cls.read(subfh)
                    subfh.seek(0)
                    subfh.truncate()
                if not line:
                    break
                subfh.write(line)


##############################################################################
#
# User database


class Config:
    """A user database configuration"""

    def __init__(self, **kwargs) -> None:
        if kwargs:
            raise ValueError("Unexpected arguments: %s" % ", ".join(kwargs))


Config_ = Config
User_ = User
Group_ = Group


class Database:
    """A user database"""

    Config: ClassVar[Type[Config_]]
    """Configuration class for this database"""

    User: Type[User_]
    """User class for this database"""

    Group: Type[Group_]
    """Group class for this database"""

    config: Config_
    """Configuration for this database"""

    def __init__(self, **kwargs) -> None:
        self.config = self.Config(**kwargs)
        # Construct User and Group classes attached to this database
        db = weakref.proxy(self)
        self.User = type(self.User.__name__, (self.User,), {'db': db})
        self.Group = type(self.Group.__name__, (self.Group,), {'db': db})

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
    def watch(self, cookie=None, persist=True, trace=False):
        """Watch for database changes"""

    def trace(self, fh=None, cookiefh=None, **kwargs):
        """Log database changes to a trace file"""
        if fh is None:
            fh = sys.stdout
        if cookiefh is None:
            cookie = None
        else:
            cookiefh.seek(0)
            cookie = cookiefh.read() or None
        for entry in self.watch(cookie=cookie, trace=True, **kwargs):
            if isinstance(entry, TraceEvent):
                entry.write(fh)
                fh.flush()
            elif isinstance(entry, SyncCookie) and cookiefh is not None:
                cookie = str(entry)
                cookiefh.truncate(0)
                cookiefh.seek(0)
                cookiefh.write(cookie)
                cookiefh.flush()


State_ = State


class WritableDatabase(Database):
    """A writable user database"""

    State: ClassVar[Type[State_]]
    """State class for this database"""

    state: State_
    """Synchronization state"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        db = weakref.proxy(self)
        self.state = self.State(db)

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


##############################################################################
#
# Synchronization identifiers


class SyncId(UUID):
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

    def __init__(self, *args, uuid: UUID = None, **kwargs) -> None:
        if uuid is not None:
            kwargs['bytes'] = uuid.bytes
            super().__init__(*args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


@dataclass
class SyncIds(Iterable):
    """A list of synchronization identifiers"""

    iterable: Iterable

    def __iter__(self):
        return iter(self.iterable)


class UnchangedSyncIds(SyncIds):
    """A list of synchronization identifiers for unchanged database entries"""


class DeletedSyncIds(SyncIds):
    """A list of synchronization identifiers for deleted database entries"""


@dataclass
class RefreshComplete:
    """An indication that the refresh stage of synchronization is complete"""

    autodelete: bool = False
