"""SQLAlchemy user database"""

from abc import abstractmethod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from .base import Attribute, Entry, User, Group, Config, WritableDatabase


class SqlAttribute(Attribute):
    """A SQL user database attribute"""
    # pylint: disable=too-few-public-methods

    def __get__(self, instance, owner):
        """Get attribute value"""
        if instance is None:
            return self
        return getattr(instance.row, self.name)

    def __set__(self, instance, value):
        """Set attribute value"""
        setattr(instance.row, self.name, value)


class SqlEntry(Entry):
    """A SQL user database entry"""

    def __init__(self, key):
        super(SqlEntry, self).__init__(key)
        if isinstance(type(self.key), DeclarativeMeta):

            # Key is a prefetched SQLAlchemy row
            self.row = self.key
            self.key = getattr(self.row, self.column)

        else:

            # Key is a column value
            query = self.db.query(self.model).filter(
                getattr(self.model, self.column) == self.key
            )
            self.row = query.one()

    @property
    @abstractmethod
    def model(self):
        """ORM model class"""
        pass

    @property
    @abstractmethod
    def column(self):
        """Key column"""
        pass


class SqlUser(SqlEntry, User):
    """A SQL user database user"""
    # pylint: disable=abstract-method
    pass


class SqlGroup(SqlEntry, Group):
    """A SQL user database group"""
    # pylint: disable=abstract-method
    pass


class SqlConfig(Config):
    """SQL user database configuration"""
    # pylint: disable=too-few-public-methods

    def __init__(self, uri, **kwargs):
        super(SqlConfig, self).__init__(**kwargs)
        self.uri = uri


class SqlDatabase(WritableDatabase):
    """A SQL user database"""

    Config = SqlConfig
    User = SqlUser
    Group = SqlGroup

    def __init__(self, **kwargs):
        super(SqlDatabase, self).__init__(**kwargs)
        self.engine = create_engine(self.config.uri, **self.config.options)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.config.uri)

    def query(self, *args, **kwargs):
        """Query database"""
        return self.session.query(*args, **kwargs)

    @property
    def users(self):
        """All users"""
        return (self.user(x) for x in self.query(self.User.model))

    @property
    def groups(self):
        """All groups"""
        return (self.group(x) for x in self.query(self.Group.model))

    def commit(self):
        """Commit database changes"""
        self.session.commit()
