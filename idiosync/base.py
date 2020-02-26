"""User database"""

from __future__ import annotations

from abc import abstractmethod
from collections import abc, UserString
from dataclasses import dataclass
import io
import itertools
import sys
from typing import (Any, ClassVar, Generic, Iterable, Iterator, Optional,
                    TextIO, Type, TypeVar, Union)
from uuid import UUID
import weakref


T_Config = TypeVar('T_Config', bound='Config')
T_Database = TypeVar('T_Database', bound='Database')
T_Entry = TypeVar('T_Entry', bound='Entry')
T_Group = TypeVar('T_Group', bound='Group')
T_State = TypeVar('T_State', bound='State')
T_TraceEvent = TypeVar('T_TraceEvent', bound='TraceEvent')
T_User = TypeVar('T_User', bound='User')
T_WritableEntry = TypeVar('T_WritableEntry', bound='WritableEntry')
T_WritableGroup = TypeVar('T_WritableGroup', bound='WritableGroup')
T_WritableUser = TypeVar('T_WritableUser', bound='WritableUser')


##############################################################################
#
# User database entries


@dataclass
class Attribute:
    """A user database entry attribute"""

    name: Optional[str] = None
    multi: bool = False

    def __set_name__(self, owner: type, name: str) -> None:
        if self.name is None:
            self.name = name


class Entry(Generic[T_Database]):
    """A user database entry"""

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self.key)

    def __str__(self) -> str:
        return str(self.key)

    db: ClassVar[T_Database]
    """Containing user database

    This is populated as a class attribute when the containing
    user database class is instantiated.
    """

    @property
    @abstractmethod
    def key(self) -> str:
        """Canonical lookup key"""

    @property
    @abstractmethod
    def uuid(self) -> UUID:
        """Permanent identifier for this entry"""

    @property
    def enabled(self) -> bool:
        """User database entry is enabled"""
        return True

    @classmethod
    @abstractmethod
    def find(cls: Type[T_Entry], key: str) -> Optional[T_Entry]:
        """Look up user database entry"""

    @classmethod
    def prepare(cls) -> None:
        """Prepare for use as part of an idiosync user database"""


class User(Entry[T_Database], Generic[T_Database, T_Group]):
    """A user"""

    def __repr__(self) -> str:
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.user(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def groups(self) -> Iterator[T_Group]:
        """Groups of which this user is a member"""


class Group(Entry[T_Database], Generic[T_Database, T_User]):
    """A group"""

    def __repr__(self) -> str:
        # Call __repr__ explicitly to bypass weakproxy
        return "%s.group(%r)" % (self.db.__repr__(), self.key)

    @property
    @abstractmethod
    def users(self) -> Iterator[T_User]:
        """Users who are members of this group"""


class WritableEntry(Entry[T_Database], Generic[T_Database]):
    """A writable user database entry"""

    @property
    @abstractmethod
    def syncid(self) -> UUID:
        """Synchronization identifier"""

    @classmethod
    def find_syncid(cls: Type[T_WritableEntry],
                    syncid: UUID) -> Optional[T_WritableEntry]:
        """Look up user database entry by synchronization identifier"""
        return next(cls.find_syncids({syncid}), None)

    @classmethod
    @abstractmethod
    def find_syncids(cls: Type[T_WritableEntry], syncids: Iterable[UUID],
                     invert: bool = False) -> Iterator[T_WritableEntry]:
        """Look up user database entries by synchronization identifier"""

    @classmethod
    def find_match(cls: Type[T_WritableEntry],
                   entry: Entry) -> Optional[T_WritableEntry]:
        """Look up closest matching user database entry"""
        return cls.find(entry.key)

    @classmethod
    @abstractmethod
    def create(cls: Type[T_WritableEntry]) -> T_WritableEntry:
        """Create new user database entry"""

    @abstractmethod
    def delete(self) -> None:
        """Delete user database entry"""


class WritableUser(WritableEntry[T_Database], User[T_Database, T_Group],
                   Generic[T_Database, T_Group]):
    """A writable user"""


class WritableGroup(WritableEntry[T_Database], Group[T_Database, T_User],
                    Generic[T_Database, T_User]):
    """A writable group"""


##############################################################################
#
# User database synchronization state


class SyncCookie(UserString):
    """A synchronization cookie"""

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self.data)


@dataclass  # type: ignore[misc]
class State(abc.MutableMapping):
    """User database synchronization state"""

    db: Database

    KEY_LEN: ClassVar[int] = 128
    """Maximum state key length"""

    KEY_COOKIE: ClassVar[str] = 'cookie'
    """Synchronization cookie state key"""

    def prepare(self) -> None:
        """Prepare for use as part of an idiosync user database"""

    @property
    def cookie(self) -> Optional[SyncCookie]:
        """Synchronization cookie"""
        raw = self.get(self.KEY_COOKIE, None)
        return SyncCookie(raw) if raw is not None else None

    @cookie.setter
    def cookie(self, value: SyncCookie) -> None:
        """Synchronization cookie"""
        self[self.KEY_COOKIE] = str(value)


##############################################################################
#
# Tracing


class TraceEvent:
    """A database trace event"""

    def __str__(self) -> str:
        with io.StringIO() as buf:
            self.write(buf)
            return buf.getvalue()

    @abstractmethod
    def write(self, fh: TextIO) -> None:
        """Write trace event to output file"""

    @classmethod
    @abstractmethod
    def read(cls: Type[T_TraceEvent], fh: TextIO) -> T_TraceEvent:
        """Read trace event from input file"""

    @classmethod
    @abstractmethod
    def delimiter(cls, line: str) -> bool:
        """Test for start-of-event delimiter in input file"""

    @classmethod
    def readall(cls: Type[T_TraceEvent],
                fh: TextIO) -> Iterator[T_TraceEvent]:
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

    def __init__(self, *args: Any, uuid: UUID = None, **kwargs: Any) -> None:
        if uuid is not None:
            kwargs['bytes'] = uuid.bytes
            super().__init__(*args, **kwargs)
        else:
            super().__init__(*args, **kwargs)


@dataclass
class SyncIds(abc.Iterable):
    """A list of synchronization identifiers"""

    iterable: Iterable[SyncId]

    def __iter__(self) -> Iterator[SyncId]:
        return iter(self.iterable)


class UnchangedSyncIds(SyncIds):
    """A list of synchronization identifiers for unchanged database entries"""


class DeletedSyncIds(SyncIds):
    """A list of synchronization identifiers for deleted database entries"""


@dataclass
class RefreshComplete:
    """An indication that the refresh stage of synchronization is complete"""

    autodelete: bool = False


##############################################################################
#
# User database


class Config:
    """A user database configuration"""

    def __init__(self, **kwargs: Any) -> None:
        if kwargs:
            raise ValueError("Unexpected arguments: %s" % ", ".join(kwargs))


class Database(Generic[T_Config, T_User, T_Group]):
    """A user database"""

    Config: ClassVar[Type[T_Config]]
    """Configuration class for this database"""

    User: Type[T_User]
    """User class for this database"""

    Group: Type[T_Group]
    """Group class for this database"""

    config: T_Config
    """Configuration for this database"""

    def __init__(self, **kwargs: Any) -> None:
        self.config = self.Config(**kwargs)
        # Construct User and Group classes attached to this database
        db = weakref.proxy(self)
        self.User = type(self.User.__name__, (self.User,), {'db': db})
        self.Group = type(self.Group.__name__, (self.Group,), {'db': db})

    def user(self, key: str) -> Optional[T_User]:
        """Look up user"""
        return self.User.find(key)

    def group(self, key: str) -> Optional[T_Group]:
        """Look up group"""
        return self.Group.find(key)

    def find(self, key: str) -> Optional[Union[T_User, T_Group]]:
        """Look up user database entry"""
        entry: Optional[Union[T_User, T_Group]]
        entry = self.user(key)
        if entry is None:
            entry = self.group(key)
        return entry

    @property
    @abstractmethod
    def users(self) -> Iterable[T_User]:
        """All users"""

    @property
    @abstractmethod
    def groups(self) -> Iterable[T_Group]:
        """All groups"""

    def prepare(self) -> None:
        """Prepare for use as an idiosync user database"""
        self.User.prepare()
        self.Group.prepare()


WatchResult = Union[T_User, T_Group, SyncCookie, UnchangedSyncIds,
                    DeletedSyncIds, RefreshComplete, TraceEvent]


class WatchableDatabase(Database[T_Config, T_User, T_Group]):
    """A watchable user database"""

    @abstractmethod
    def watch(self, cookie: str = None, persist: bool = True,
              trace: bool = False) -> Iterator[WatchResult[T_User, T_Group]]:
        """Watch for database changes"""

    def trace(self, fh: Optional[TextIO] = None,
              cookiefh: Optional[TextIO] = None, **kwargs: Any) -> None:
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


class WritableDatabase(Database[T_Config, T_WritableUser, T_WritableGroup],
                       Generic[T_Config, T_WritableUser, T_WritableGroup,
                               T_State]):
    """A writable user database"""

    State: ClassVar[Type[T_State]]
    """State class for this database"""

    state: T_State
    """Synchronization state"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        db = weakref.proxy(self)
        self.state = self.State(db)

    def find_syncids(self, syncids: Iterable[UUID],
                     invert: bool = False) -> Iterator[Union[T_WritableUser,
                                                             T_WritableGroup]]:
        """Look up user database entries by synchronization identifier"""
        return itertools.chain(
            self.User.find_syncids(syncids, invert=invert),
            self.Group.find_syncids(syncids, invert=invert)
        )

    @abstractmethod
    def commit(self) -> None:
        """Commit database changes"""

    def prepare(self) -> None:
        """Prepare for use as an idiosync user database"""
        super().prepare()
        self.state.prepare()
