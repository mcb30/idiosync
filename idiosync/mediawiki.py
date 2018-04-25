"""MediaWiki user database"""

from sqlalchemy import TypeDecorator, Column, ForeignKey, Integer, Unicode
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .base import Group
from .sqlalchemy import SqlAttribute, SqlUser, SqlConfig, SqlDatabase

##############################################################################
#
# SQLAlchemy ORM


Base = declarative_base()


class BinaryString(TypeDecorator):
    """MediaWiki Unicode string held in a binary column

    Apparently MySQL's support for Unicode has historically been so
    badly broken that applications such as MediaWiki have chosen to
    use raw binary columns and handle character encoding and decoding
    entirely at the application level.
    """

    impl = Unicode
    python_type = str

    def process_bind_param(self, value, dialect):
        """Encode Unicode string to raw column value"""
        return value.encode('utf-8')

    def process_result_value(self, value, dialect):
        """Decode raw column value to Unicode string"""
        return value.decode('utf-8')

    def process_literal_param(self, value, dialect):
        """Encode Unicode string to inline literal value"""
        return value


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

    model = OrmUser
    column = 'user_name'

    name = SqlAttribute('user_name')
    displayName = SqlAttribute('user_real_name')
    mail = SqlAttribute('user_email')

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


class MediaWikiConfig(SqlConfig):
    """MediaWiki user database configuration"""
    # pylint: disable=too-few-public-methods
    pass


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
