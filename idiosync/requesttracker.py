"""Request Tracker (RT) user database"""

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from .sqlalchemy import (UuidChar, SqlModel, SqlAttribute, SqlEntry, SqlUser,
                         SqlGroup, SqlConfig, SqlDatabase)

##############################################################################
#
# SQLAlchemy ORM


Base = declarative_base()


class OrmPrincipal(Base):
    """An RT security principal"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'Principals'

    id = Column(Integer, primary_key=True)
    PrincipalType = Column(Enum('User', 'Group', native_enum=False),
                           nullable=False)
    Disabled = Column(Integer, nullable=False, default=0)

    user = relationship('OrmUser', back_populates='principal')
    group = relationship('OrmGroup', back_populates='principal')


class OrmUser(Base):
    """An RT user"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'Users'

    def __init__(self, *args, **kwargs):
        principal = OrmPrincipal(PrincipalType='User')
        super(OrmUser, self).__init__(*args, principal=principal, **kwargs)

    id = Column(ForeignKey('Principals.id'), primary_key=True)
    Name = Column(String, nullable=False, unique=True)
    EmailAddress = Column(String)
    RealName = Column(String)
    WorkPhone = Column(String)
    MobilePhone = Column(String)
    IdiosyncId = Column(UuidChar, unique=True)

    principal = relationship('OrmPrincipal', back_populates='user')
    memberships = relationship('OrmMember', back_populates='user')
    groups = association_proxy('memberships', 'group')


class OrmGroup(Base):
    """An RT group"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'Groups'

    def __init__(self, *args, **kwargs):
        principal = OrmPrincipal(PrincipalType='Group')
        super(OrmGroup, self).__init__(*args, principal=principal, **kwargs)

    id = Column(ForeignKey('Principals.id'), primary_key=True)
    Name = Column(String, unique=True)
    Description = Column(String)
    IdiosyncId = Column(UuidChar, unique=True)

    principal = relationship('OrmPrincipal', back_populates='group')
    memberships = relationship('OrmMember', back_populates='group')
    users = association_proxy('memberships', 'user')


class OrmMember(Base):
    """An RT group membership"""
    # pylint: disable=too-few-public-methods

    __tablename__ = 'GroupMembers'

    id = Column(Integer, primary_key=True)
    GroupId = Column(ForeignKey('Groups.id'), nullable=False)
    MemberId = Column(ForeignKey('Users.id'), nullable=False)

    user = relationship('OrmUser', back_populates='memberships',
                        lazy='joined')
    group = relationship('OrmGroup', back_populates='memberships',
                         lazy='joined')


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
    # pylint: disable=too-many-ancestors

    model = SqlModel(OrmUser, 'Name', syncid='IdiosyncId', member='groups')
    displayName = SqlAttribute('RealName')
    mail = SqlAttribute('EmailAddress')
    mobile = SqlAttribute('MobilePhone')
    telephoneNumber = SqlAttribute('WorkPhone')
    uid = SqlAttribute('Name')


class RequestTrackerGroup(SqlGroup, RequestTrackerEntry):
    """An RT group"""
    # pylint: disable=too-many-ancestors

    model = SqlModel(OrmGroup, 'Name', syncid='IdiosyncId', member='users')
    commonName = SqlAttribute('Name')
    description = SqlAttribute('Description')


class RequestTrackerConfig(SqlConfig):
    """RT user database configuration"""
    # pylint: disable=too-few-public-methods
    pass


class RequestTrackerDatabase(SqlDatabase):
    """An RT user database"""
    # pylint: disable=too-few-public-methods

    Config = RequestTrackerConfig
    User = RequestTrackerUser
    Group = RequestTrackerGroup
