"""LDAP user database"""

from abc import abstractmethod
import logging
import uuid
import ldap
import ldap.controls.psearch
from .base import Attribute, Entry, User, Group, Config, WatchableDatabase

logger = logging.getLogger(__name__)

##############################################################################
#
# Exceptions


class LdapUnrecognisedEntryError(Exception):
    """Unrecognised LDAP database entry"""

    def __str__(self):
        return 'Unrecognised entry %s' % self.args


##############################################################################
#
# LDAP attributes


class LdapAttribute(Attribute):
    """An LDAP attribute"""
    # pylint: disable=too-few-public-methods

    def __get__(self, instance, owner):
        """Get attribute value"""

        # Allow attribute object to be retrieved
        if instance is None:
            return self

        # Parse and return as list or single value as applicable
        attr = [self.parse(x) for x in instance.attrs.get(self.name, ())]
        return attr if self.multi else attr[0] if attr else None

    @staticmethod
    @abstractmethod
    def parse(value):
        """Parse attribute value"""
        pass


class LdapStringAttribute(LdapAttribute):
    """A string-valued LDAP attribute"""
    # pylint: disable=too-few-public-methods

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return bytes.decode(value)


class LdapNumericAttribute(LdapAttribute):
    """A numeric LDAP attribute"""
    # pylint: disable=too-few-public-methods

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return int(value)


class LdapUuidAttribute(LdapAttribute):
    """A UUID LDAP attribute"""
    # pylint: disable=too-few-public-methods

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return uuid.UUID(value.decode())


##############################################################################
#
# LDAP entries


class LdapSearch(object):
    """An LDAP search filter"""

    def __init__(self, objectClass, key, member):
        self.objectClass = objectClass
        self.key = key
        self.member = member

    @property
    def all(self):
        """Search filter for all entries"""
        return '(objectClass=%s)' % self.objectClass

    def single(self, key):
        """Search filter for a single entry"""
        return '(&%s(%s=%s))' % (self.all, self.key, key)

    def membership(self, other):
        """Search filter for membership"""
        return '(&%s%s)' % (self.all, self.member(other))


class LdapEntry(Entry):
    """An LDAP directory entry"""
    # pylint: disable=too-few-public-methods

    member = LdapStringAttribute('member', multi=True)
    memberOf = LdapStringAttribute('memberOf', multi=True)
    uuid = LdapUuidAttribute('entryUUID')

    def __init__(self, key):
        super(LdapEntry, self).__init__(key)
        if isinstance(self.key, tuple):

            # Key is a prefetched LDAP entry
            (self.dn, self.attrs) = self.key
            self.key = self.attrs[self.search.key][0].decode()

        else:

            # Key is a search attribute
            res = self.db.search(self.search.single(self.key))
            try:
                [(self.dn, self.attrs)] = res
            except ValueError:
                raise self.NoSuchEntryError(self.key) from None

    @property
    @abstractmethod
    def search(self):
        """Search filter"""
        pass


class LdapUser(LdapEntry, User):
    """An LDAP user"""

    search = LdapSearch('person', 'cn', lambda x: '(memberOf=%s)' % x.dn)

    commonName = LdapStringAttribute('cn')
    displayName = LdapStringAttribute('displayName')
    employeeNumber = LdapStringAttribute('employeeNumber')
    givenName = LdapStringAttribute('givenName')
    initials = LdapStringAttribute('initials')
    mail = LdapStringAttribute('mail', multi=True)
    mobile = LdapStringAttribute('mobile')
    surname = LdapStringAttribute('sn')
    telephoneNumber = LdapStringAttribute('telephoneNumber')
    title = LdapStringAttribute('title')

    name = commonName

    @property
    def groups(self):
        """Groups of which this user is a member"""
        return (self.db.group(x) for x in
                self.db.search(self.db.Group.search.membership(self)))


class LdapGroup(LdapEntry, Group):
    """An LDAP group"""

    search = LdapSearch('groupOfNames', 'cn', lambda x: '(member=%s)' % x.dn)

    commonName = LdapStringAttribute('cn')
    description = LdapStringAttribute('description')

    name = commonName

    @property
    def users(self):
        """Users who are members of this group"""
        return (self.db.user(x) for x in
                self.db.search(self.db.User.search.membership(self)))


##############################################################################
#
# LDAP database


class LdapConfig(Config):
    """LDAP user database configuration"""
    # pylint: disable=too-few-public-methods

    def __init__(self, uri=None, domain='', base=None, sasl_mech='GSSAPI',
                 username=None, password=None, **kwargs):
        super(LdapConfig, self).__init__(**kwargs)
        self.uri = uri
        self.domain = domain
        self.base = (base if base is not None else
                     ','.join('dc=%s' % x for x in self.domain.split('.')))
        self.sasl_mech = sasl_mech
        self.username = username
        self.password = password


class LdapDatabase(WatchableDatabase):
    """An LDAP user database"""

    Config = LdapConfig
    User = LdapUser
    Group = LdapGroup

    def __init__(self, **kwargs):
        super(LdapDatabase, self).__init__(**kwargs)
        self.ldap = ldap.initialize(self.config.uri)
        self.bind()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.config.base)

    def bind(self):
        """Bind to LDAP database"""
        if self.config.sasl_mech:
            # Perform SASL bind
            cb = {
                ldap.sasl.CB_AUTHNAME: self.config.username,
                ldap.sasl.CB_PASS: self.config.password
            }
            sasl = ldap.sasl.sasl(cb, self.config.sasl_mech)
            self.ldap.sasl_interactive_bind_s('', sasl)
        else:
            # Perform simple (or anonymous) bind
            self.ldap.simple_bind_s(self.config.username or '',
                                    self.config.password or '')
        logger.debug("Authenticated as %s", self.ldap.whoami_s())

    def search(self, search):
        """Search LDAP database"""
        logger.debug("Searching for %s", search)
        return self.ldap.search_s(self.config.base, ldap.SCOPE_SUBTREE,
                                  search, ['*', '+'])

    @property
    def users(self):
        """All users"""
        return (self.user(x) for x in self.search(self.User.search.all))

    @property
    def groups(self):
        """All groups"""
        return (self.group(x) for x in self.search(self.Group.search.all))

    def watch(self):
        """Watch for database changes"""
        search = '(|%s%s)' % (self.User.search.all, self.Group.search.all)
        serverctrls = [ldap.controls.psearch.PersistentSearchControl()]
        msgid = self.ldap.search_ext(self.config.base, ldap.SCOPE_SUBTREE,
                                     search, ['*', '+'],
                                     serverctrls=serverctrls)
        user_objectClass = self.User.search.objectClass.lower()
        group_objectClass = self.Group.search.objectClass.lower()
        while True:
            (res_type, res_list, *_) = self.ldap.result4(msgid, all=0)
            if not (res_type and res_list):
                return
            for dn, attrs in res_list:
                constructor = None
                for objectClass in attrs['objectClass']:
                    objectClass = objectClass.decode().lower()
                    if objectClass == user_objectClass:
                        constructor = self.user
                        break
                    elif objectClass == group_objectClass:
                        constructor = self.group
                        break
                if constructor is None:
                    raise LdapUnrecognisedEntryError(dn)
                yield constructor((dn, attrs))
