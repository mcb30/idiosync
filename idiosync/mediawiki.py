"""MediaWiki user database"""

from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from .sqlalchemy import (BinaryString, UnsignedInteger, UuidChar, SqlModel,
                         SqlAttribute, SqlUser, SqlStateModel, SqlState,
                         SqlConfig, SqlDatabase)
from .dummy import DummyGroup

##############################################################################
#
# SQLAlchemy ORM


Base = declarative_base()


class OrmUser(Base):
    """A MediaWiki user"""

    __tablename__ = 'user'

    user_id = Column(UnsignedInteger, primary_key=True)
    user_name = Column(BinaryString, nullable=False, unique=True)
    user_real_name = Column(BinaryString, nullable=False, default='')
    user_password = Column(BinaryString, nullable=False, default='')
    user_newpassword = Column(BinaryString, nullable=False, default='')
    user_email = Column(BinaryString, nullable=False, default='')

    user_groups = relationship('OrmUserGroup', back_populates='user',
                               cascade='all, delete-orphan')
    ipblocks = relationship('OrmIpBlock', back_populates='user',
                            lazy='joined', cascade='all, delete-orphan')

    idiosync_user = relationship('OrmIdiosyncUser', back_populates='user',
                                 uselist=False, lazy='joined',
                                 cascade='all, delete-orphan',
                                 passive_deletes=True)
    user_idiosyncid = association_proxy(
        'idiosync_user', 'idu_syncid',
        creator=lambda syncid: OrmIdiosyncUser(idu_syncid=syncid)
    )


class OrmUserGroup(Base):
    """A MediaWiki group membership"""

    __tablename__ = 'user_groups'

    ug_user = Column(ForeignKey('user.user_id'), primary_key=True)
    ug_group = Column(BinaryString, primary_key=True)

    user = relationship('OrmUser', back_populates='user_groups')


class OrmIpBlock(Base):
    """A MediaWiki IP or user block"""

    __tablename__ = 'ipblocks'

    ipb_id = Column(Integer, primary_key=True)
    ipb_address = Column(BinaryString, nullable=False, default='')
    ipb_user = Column(ForeignKey('user.user_id'), nullable=False)
    ipb_reason = Column(BinaryString, nullable=False, default='Disabled user')
    ipb_timestamp = Column(BinaryString, nullable=False, default=lambda:
                           datetime.now().strftime('%Y%m%d%H%M%S'))
    ipb_expiry = Column(BinaryString, nullable=False, default='infinity')
    ipb_range_start = Column(BinaryString, nullable=False, default='')
    ipb_range_end = Column(BinaryString, nullable=False, default='')

    user = relationship('OrmUser', back_populates='ipblocks')


class OrmIdiosyncUser(Base):
    """A MediaWiki user synchronization identifier"""

    __tablename__ = 'idiosync_user'

    idu_user = Column(ForeignKey('user.user_id', onupdate='CASCADE',
                                 ondelete='CASCADE'), primary_key=True)
    idu_syncid = Column(UuidChar, nullable=False, unique=True)

    user = relationship('OrmUser', back_populates='idiosync_user')


class OrmIdiosyncState(Base):
    """MediaWiki synchronization state"""

    __tablename__ = 'idiosync_state'

    ids_id = Column(Integer, primary_key=True)
    ids_key = Column(String(SqlState.KEY_LEN), nullable=False, unique=True)
    ids_value = Column(Text)


##############################################################################
#
# User database model


class MediaWikiUidAttribute(SqlAttribute):
    """A MediaWiki user name"""

    def __get__(self, instance, owner):
        """Get user name"""
        if instance is None:
            return self
        name = super().__get__(instance, owner)
        return instance.format_uid(name)

    def __set__(self, instance, value):
        """Set user name"""
        name = instance.parse_uid(value)
        super().__set__(instance, name)


class MediaWikiUser(SqlUser):
    """A MediaWiki user"""

    model = SqlModel(OrmUser, 'user_name', syncid='user_idiosyncid')
    uid = MediaWikiUidAttribute('user_name')
    displayName = SqlAttribute('user_real_name')
    mail = SqlAttribute('user_email')

    @property
    def enabled(self):
        """User is enabled"""
        return not self.row.ipblocks

    @enabled.setter
    def enabled(self, value):
        """User is enabled"""
        if value:
            self.row.ipblocks.clear()
        else:
            self.row.ipblocks.append(OrmIpBlock(ipb_address=self.uid))

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
            raise ValueError(
                "User name must begin with a lower-case character"
            )
        return name[0].upper() + name[1:]

    @classmethod
    def find_match(cls, entry):
        """Look up closest matching user database entry"""
        return cls.find(cls.parse_uid(entry.key))

    @property
    def groups(self):
        """Groups of which this user is a member"""
        return (self.db.Group(x.ug_group) for x in self.row.user_groups)


class MediaWikiGroup(DummyGroup):
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
        return (self.db.User(x) for x in query)


class MediaWikiState(SqlState):
    """MediaWiki user database synchronization state"""

    model = SqlStateModel(OrmIdiosyncState, 'ids_key', 'ids_value')


class MediaWikiConfig(SqlConfig):
    """MediaWiki user database configuration"""

    def __init__(self, title_case=True, **kwargs):
        super().__init__(**kwargs)
        self.title_case = title_case


class MediaWikiDatabase(SqlDatabase):
    """A MediaWiki user database"""

    Config = MediaWikiConfig
    User = MediaWikiUser
    Group = MediaWikiGroup
    State = MediaWikiState

    @property
    def groups(self):
        """All groups"""
        query = self.query(OrmUserGroup.ug_group).distinct()
        return (self.Group(x.ug_group) for x in query)
