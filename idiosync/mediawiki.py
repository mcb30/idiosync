"""MediaWiki user database"""

import uuid
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .base import WritableGroup
from .sqlalchemy import (BinaryString, Uuid, SqlModel, SqlAttribute, SqlUser,
                         SqlConfig, SqlDatabase)

NAMESPACE_MEDIAWIKI = uuid.UUID('c5dd5cb8-b889-431e-8426-81297a053894')

##############################################################################
#
# SQLAlchemy ORM


Base = declarative_base()


class OrmUser(Base):
    """A MediaWiki user"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'user'

    user_id = Column(Integer, primary_key=True)
    user_name = Column(BinaryString, nullable=False, unique=True)
    user_real_name = Column(BinaryString, nullable=False, default='')
    user_password = Column(BinaryString, nullable=False, default='')
    user_newpassword = Column(BinaryString, nullable=False, default='')
    user_email = Column(BinaryString, nullable=False, default='')
    user_idiosyncid = Column(Uuid, unique=True)

    user_groups = relationship('OrmUserGroup', back_populates='user')


class OrmUserGroup(Base):
    """A MediaWiki group membership"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'user_groups'

    ug_user = Column(ForeignKey('user.user_id'), primary_key=True)
    ug_group = Column(BinaryString, primary_key=True)

    user = relationship('OrmUser', back_populates='user_groups')


##############################################################################
#
# User database model


class MediaWikiUidAttribute(SqlAttribute):
    """A MediaWiki user name"""
    # pylint: disable=too-few-public-methods

    def __get__(self, instance, owner):
        """Get user name"""
        if instance is None:
            return self
        name = super(MediaWikiUidAttribute, self).__get__(instance, owner)
        return instance.format_uid(name)

    def __set__(self, instance, value):
        """Set user name"""
        name = instance.parse_uid(value)
        super(MediaWikiUidAttribute, self).__set__(instance, name)


class MediaWikiUser(SqlUser):
    """A MediaWiki user"""
    # pylint: disable=too-many-ancestors

    model = SqlModel(OrmUser, 'user_name', 'user_idiosyncid')
    uid = MediaWikiUidAttribute('user_name')
    displayName = SqlAttribute('user_real_name')
    mail = SqlAttribute('user_email')

    @classmethod
    def format_uid(cls, name):
        """Format user name to external representation"""
        if name is None:
            return None
        if not cls.db.config.title_case:
            return name
        return name[0].lower() + name[1:]

    @classmethod
    def parse_uid(cls, name):
        """Parse user name to database representation"""
        if not cls.db.config.title_case:
            return name
        if not name[0].islower():
            raise ValueError("User name must begin with a lower-case character")
        return name[0].upper() + name[1:]

    @classmethod
    def find_match(cls, entry):
        """Look up closest matching user database entry"""
        return cls.find(cls.parse_uid(entry.key))

    @property
    def groups(self):
        """Groups of which this user is a member"""
        return (self.db.Group(x.ug_group) for x in self.row.user_groups)


class MediaWikiGroup(WritableGroup):
    """A MediaWiki group

    The MediaWiki database has no table for group definitions: groups
    exist solely as free text strings mentioned as group names within
    the ``user_group`` table.  A group exists if and only if it has
    members; there is no separate concept of group existence.
    """

    key = None

    def __init__(self, key):
        self.key = key

    @property
    def uuid(self):
        """Permanent identifier for this entry"""
        # Generate UUID from group name since there is no concept of
        # permanent identity for MediaWiki groups
        return uuid.uuid5(NAMESPACE_MEDIAWIKI, self.key)

    @property
    def syncid(self):
        """Synchronization identifier"""
        return None

    @syncid.setter
    def syncid(self, value):
        """Set synchronization identifier"""
        pass

    @classmethod
    def find(cls, key):
        """Look up user database entry"""
        return cls(key)

    @classmethod
    def find_syncid(cls, syncid):
        """Look up user database entry by synchronization identifier"""
        return None

    @classmethod
    def create(cls):
        """Create new user database entry"""
        return cls(None)

    @classmethod
    def delete(cls, syncids):
        """Delete all of the specified entries"""
        pass

    @classmethod
    def prune(cls, syncids):
        """Delete all synchronized entries except the specified entries"""
        pass

    @property
    def users(self):
        """Users who are members of this group"""
        query = self.db.query(OrmUser).join(OrmUserGroup).filter(
            OrmUserGroup.ug_group == self.key
        )
        return (self.db.User(x) for x in query)


class MediaWikiConfig(SqlConfig):
    """MediaWiki user database configuration"""
    # pylint: disable=too-few-public-methods

    def __init__(self, title_case=True, **kwargs):
        super(MediaWikiConfig, self).__init__(**kwargs)
        self.title_case = title_case


class MediaWikiDatabase(SqlDatabase):
    """A MediaWiki user database"""
    # pylint: disable=too-few-public-methods

    Config = MediaWikiConfig
    User = MediaWikiUser
    Group = MediaWikiGroup

    @property
    def groups(self):
        """All groups"""
        query = self.query(OrmUserGroup.ug_group).distinct()
        return (self.Group(x.ug_group) for x in query)
