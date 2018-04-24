"""User database"""

from abc import ABC, abstractmethod

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


class Entry(ABC):
    """A user database entry"""
    # pylint: disable=too-few-public-methods

    NoSuchEntryError = NoSuchEntryError

    def __init__(self, db, key):
        self.db = db
        self.key = key

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.key)

    @staticmethod
    def match(other):
        """Identify matching user database entry"""
        return other.key


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
    pass


class Database(ABC):
    """A user database"""

    def __init__(self, **kwargs):
        self.config = self.Config(**kwargs)

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
        return self.User(self, key)

    def group(self, key):
        """Fetch group"""
        if isinstance(key, Group):
            key = self.Group.match(key)
        return self.Group(self, key)

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


class WatchableDatabase(Database):
    """A watchable user database"""

    @abstractmethod
    def watch(self):
        """Watch for database changes"""
        pass
