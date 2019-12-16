"""Request Tracker (RT) user database"""

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from .sqlalchemy import (UuidChar, SqlModel, SqlAttribute, SqlEntry, SqlUser,
                         SqlGroup, SqlStateModel, SqlState, SqlConfig,
                         SqlDatabase)

##############################################################################
#
# SQLAlchemy ORM


Base = declarative_base()


class OrmPrincipal(Base):
    """An RT security principal"""

    __tablename__ = 'Principals'

    id = Column(Integer, primary_key=True)
    PrincipalType = Column(Enum('User', 'Group', native_enum=False),
                           nullable=False)
    Disabled = Column(Integer, nullable=False, default=0)

    user = relationship('OrmUser', back_populates='principal')
    group = relationship('OrmGroup', back_populates='principal')


class OrmUser(Base):
    """An RT user"""

    __tablename__ = 'Users'

    def __init__(self, *args, **kwargs):
        principal = OrmPrincipal(PrincipalType='User')
        super().__init__(*args, principal=principal, **kwargs)

    id = Column(ForeignKey('Principals.id'), primary_key=True)
    Name = Column(String, nullable=False, unique=True)
    EmailAddress = Column(String)
    RealName = Column(String)
    WorkPhone = Column(String)
    MobilePhone = Column(String)

    principal = relationship('OrmPrincipal', back_populates='user',
                             lazy='joined')
    memberships = relationship('OrmMember', back_populates='user')
    groups = association_proxy('memberships', 'group')

    idiosync_user = relationship('OrmIdiosyncUser', back_populates='user',
                                 uselist=False, lazy='joined',
                                 cascade='all, delete-orphan',
                                 passive_deletes=True)
    IdiosyncId = association_proxy(
        'idiosync_user', 'IdiosyncId',
        creator=lambda syncid: OrmIdiosyncUser(IdiosyncId=syncid)
    )


class OrmGroup(Base):
    """An RT group"""

    __tablename__ = 'Groups'

    def __init__(self, *args, **kwargs):
        principal = OrmPrincipal(PrincipalType='Group')
        super().__init__(*args, principal=principal, **kwargs)

    id = Column(ForeignKey('Principals.id'), primary_key=True)
    Name = Column(String, unique=True)
    Description = Column(String)

    principal = relationship('OrmPrincipal', back_populates='group',
                             lazy='joined')
    memberships = relationship('OrmMember', back_populates='group')
    users = association_proxy('memberships', 'user')

    idiosync_group = relationship('OrmIdiosyncGroup', back_populates='group',
                                  uselist=False, lazy='joined',
                                  cascade='all, delete-orphan',
                                  passive_deletes=True)
    IdiosyncId = association_proxy(
        'idiosync_group', 'IdiosyncId',
        creator=lambda syncid: OrmIdiosyncGroup(IdiosyncId=syncid)
    )


class OrmMember(Base):
    """An RT group membership"""

    __tablename__ = 'GroupMembers'

    id = Column(Integer, primary_key=True)
    GroupId = Column(ForeignKey('Groups.id'), nullable=False)
    MemberId = Column(ForeignKey('Users.id'), nullable=False)

    user = relationship('OrmUser', back_populates='memberships',
                        lazy='joined')
    group = relationship('OrmGroup', back_populates='memberships',
                         lazy='joined')


class OrmIdiosyncUser(Base):
    """An RT user synchronization identifier"""

    __tablename__ = 'IdiosyncUser'

    id = Column(ForeignKey('Users.id', onupdate='CASCADE', ondelete='CASCADE'),
                primary_key=True)
    IdiosyncId = Column(UuidChar, unique=True)

    user = relationship('OrmUser', back_populates='idiosync_user')


class OrmIdiosyncGroup(Base):
    """An RT group synchronization identifier"""

    __tablename__ = 'IdiosyncGroup'

    id = Column(ForeignKey('Groups.id', onupdate='CASCADE',
                           ondelete='CASCADE'),
                primary_key=True)
    IdiosyncId = Column(UuidChar, unique=True)

    group = relationship('OrmGroup', back_populates='idiosync_group')


class OrmIdiosyncState(Base):
    """RT synchronization state"""

    __tablename__ = 'IdiosyncState'

    id = Column(Integer, primary_key=True)
    Key = Column(String(SqlState.KEY_LEN), nullable=False, unique=True)
    Value = Column(Text)


##############################################################################
#
# User database model


class RequestTrackerEntry(SqlEntry):
    """An RT user database entry"""

    @property
    def enabled(self):
        """User database entry is enabled"""
        return not self.row.principal.Disabled

    @enabled.setter
    def enabled(self, value):
        """User database entry is enabled"""
        self.row.principal.Disabled = (0 if value else 1)


class RequestTrackerUser(SqlUser, RequestTrackerEntry):
    """An RT user"""

    model = SqlModel(OrmUser, 'Name', syncid='IdiosyncId', member='groups')
    displayName = SqlAttribute('RealName')
    mail = SqlAttribute('EmailAddress')
    mobile = SqlAttribute('MobilePhone')
    telephoneNumber = SqlAttribute('WorkPhone')
    uid = SqlAttribute('Name')


class RequestTrackerGroup(SqlGroup, RequestTrackerEntry):
    """An RT group"""

    model = SqlModel(OrmGroup, 'Name', syncid='IdiosyncId', member='users')
    commonName = SqlAttribute('Name')
    description = SqlAttribute('Description')


class RequestTrackerState(SqlState):
    """RT user database synchronization state"""

    model = SqlStateModel(OrmIdiosyncState, 'Key', 'Value')


class RequestTrackerConfig(SqlConfig):
    """RT user database configuration"""


class RequestTrackerDatabase(SqlDatabase):
    """An RT user database"""

    Config = RequestTrackerConfig
    User = RequestTrackerUser
    Group = RequestTrackerGroup
    State = RequestTrackerState
