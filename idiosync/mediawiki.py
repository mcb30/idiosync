"""MediaWiki user database"""

import uuid
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .base import Group
from .sqlalchemy import (BinaryString, SqlModel, SqlAttribute, SqlUser,
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
    user_real_name = Column(BinaryString, nullable=False)
    user_email = Column(BinaryString, nullable=False)

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


class MediaWikiUser(SqlUser):
    """A MediaWiki user"""

    model = SqlModel(OrmUser, 'user_name')

    displayName = SqlAttribute('user_real_name')
    mail = SqlAttribute('user_email')

    @classmethod
    def format_name(cls, name):
        """Format user name to external representation"""
        if not cls.db.config.title_case:
            return name
        return name[0].lower() + name[1:]

    @classmethod
    def parse_name(cls, name):
        """Parse user name to database representation"""
        if not cls.db.config.title_case:
            return name
        if not name[0].islower():
            raise ValueError("User name must begin with a lower-case character")
        return name[0].upper() + name[1:]

    @property
    def name(self):
        """User name"""
        return self.format_name(self.row.user_name)

    @name.setter
    def name(self, value):
        """User name"""
        self.row.user_name = self.parse_name(value)

    @classmethod
    def match(cls, other):
        """Identify matching user database entry"""
        return cls.parse_name(other.name)

    @property
    def groups(self):
        """Groups of which this user is a member"""
        return (self.db.group(x.ug_group) for x in self.row.user_groups)


class MediaWikiGroup(Group):
    """A MediaWiki group

    The MediaWiki database has no table for group definitions: groups
    exist solely as free text strings mentioned as group names within
    the ``user_group`` table.
    """

    @property
    def users(self):
        """Users who are members of this group"""
        query = self.db.query(OrmUser).join(OrmUserGroup).filter(
            OrmUserGroup.ug_group == self.key
        )
        return (self.db.user(x) for x in query)

    @property
    def uuid(self):
        """Permanent identifier for this entry"""
        # Generate UUID from group name since there is no concept of
        # permanent identity for MediaWiki groups
        return uuid.uuid5(NAMESPACE_MEDIAWIKI, self.key)


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
        return (self.group(x.ug_group) for x in query)
