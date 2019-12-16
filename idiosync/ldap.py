"""LDAP user database"""

from abc import abstractmethod
from collections import namedtuple
import logging
import uuid
import ldap
from ldap.syncrepl import (SyncRequestControl, SyncStateControl,
                           SyncDoneControl)
from .base import (Attribute, Entry, User, Group, Config, WatchableDatabase,
                   SyncId, UnchangedSyncIds, DeletedSyncIds, RefreshComplete,
                   SyncCookie)
from .syncrepl import SyncInfoMessage

logger = logging.getLogger(__name__)

##############################################################################
#
# Base types

LdapResult = namedtuple('LdapResult',
                        ['type', 'data', 'msgid', 'ctrls', 'name', 'value'])


class LdapAttributeDict(dict):
    """An LDAP attribute dictionary"""

    def __init__(self, raw):
        # Force all keys to lower case
        super().__init__({k.lower(): v for k, v in raw.items()})


##############################################################################
#
# Exceptions


class LdapProtocolError(Exception):
    """LDAP protocol error"""

    def __str__(self):
        return "Protocol error: %s" % self.args


class LdapUnrecognisedEntryError(Exception):
    """Unrecognised LDAP database entry"""

    def __str__(self):
        return "Unrecognised entry %s" % self.args


class LdapSyncIdMismatchError(Exception):
    """SyncId does not match UUID attribute"""

    def __str__(self):
        return "SyncId %s mismatch for entry %s (%s)" % self.args


##############################################################################
#
# LDAP attributes


class LdapAttribute(Attribute):
    """An LDAP attribute"""

    def __get__(self, instance, owner):
        """Get attribute value"""

        # Allow attribute object to be retrieved
        if instance is None:
            return self

        # Parse and return as list or single value as applicable
        attr = [self.parse(x)
                for x in instance.attrs.get(self.name.lower(), ())]
        return attr if self.multi else attr[0] if attr else None

    @staticmethod
    @abstractmethod
    def parse(value):
        """Parse attribute value"""


class LdapStringAttribute(LdapAttribute):
    """A string-valued LDAP attribute"""

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return bytes.decode(value)


class LdapNumericAttribute(LdapAttribute):
    """A numeric LDAP attribute"""

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return int(value)


class LdapBooleanAttribute(LdapAttribute):
    """A boolean LDAP attribute"""

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return value.lower() == b'true'


class LdapUuidAttribute(LdapAttribute):
    """A UUID LDAP attribute"""

    @staticmethod
    def parse(value):
        """Parse attribute value"""
        return uuid.UUID(value.decode())


class LdapEntryUuidAttribute(LdapUuidAttribute):
    """An EntryUUID LDAP attribute"""

    def __set__(self, instance, value):
        # Allow EntryUUID to be populated from syncStateControl value
        instance.attrs[self.name.lower()] = [str(value).encode()]


##############################################################################
#
# LDAP entries


class LdapModel:
    """An LDAP model"""

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

    member = LdapStringAttribute('member', multi=True)
    memberOf = LdapStringAttribute('memberOf', multi=True)
    uuid = LdapEntryUuidAttribute('entryUUID')

    model = None
    """LDAP model"""

    def __init__(self, dn, attrs):
        super().__init__()
        self.dn = dn
        self.attrs = (attrs if isinstance(attrs, LdapAttributeDict)
                      else LdapAttributeDict(attrs))

    @property
    def key(self):
        """Canonical lookup key"""
        return self.attrs[self.model.key.lower()][0].decode()

    @classmethod
    def find(cls, key):
        """Look up user database entry"""
        res = cls.db.search(cls.model.single(key))
        try:
            [(dn, attrs)] = res
        except ValueError:
            return None
        return cls(dn, attrs)


class LdapUser(LdapEntry, User):
    """An LDAP user"""

    model = LdapModel('person', 'cn', lambda x: '(memberOf=%s)' % x.dn)

    commonName = LdapStringAttribute('cn')
    displayName = LdapStringAttribute('displayName')
    employeeNumber = LdapStringAttribute('employeeNumber')
    givenName = LdapStringAttribute('givenName')
    initials = LdapStringAttribute('initials')
    mail = LdapStringAttribute('mail', multi=True)
    mobile = LdapStringAttribute('mobile', multi=True)
    surname = LdapStringAttribute('sn')
    telephoneNumber = LdapStringAttribute('telephoneNumber', multi=True)
    title = LdapStringAttribute('title')

    name = commonName

    @property
    def groups(self):
        """Groups of which this user is a member"""
        return (self.db.Group(dn, attrs) for dn, attrs in
                self.db.search(self.db.Group.model.membership(self)))


class LdapGroup(LdapEntry, Group):
    """An LDAP group"""

    model = LdapModel('groupOfNames', 'cn', lambda x: '(member=%s)' % x.dn)

    commonName = LdapStringAttribute('cn')
    description = LdapStringAttribute('description')

    name = commonName

    @property
    def users(self):
        """Users who are members of this group"""
        return (self.db.User(dn, attrs) for dn, attrs in
                self.db.search(self.db.User.model.membership(self)))


##############################################################################
#
# LDAP database


class LdapConfig(Config):
    """LDAP user database configuration"""

    def __init__(self, uri=None, domain='', base=None, sasl_mech='GSSAPI',
                 username=None, password=None, **kwargs):
        # pylint: disable=too-many-arguments
        super().__init__(**kwargs)
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
        super().__init__(**kwargs)
        self.ldap = ldap.initialize(self.config.uri, **self.config.options)
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
        # pylint: disable=no-member
        logger.debug("Searching for %s", search)
        return self.ldap.search_s(self.config.base,
                                  # pylint: disable=no-member
                                  ldap.SCOPE_SUBTREE, search, ['*', '+'])

    @property
    def users(self):
        """All users"""
        return (self.User(dn, attrs) for dn, attrs in
                self.search(self.User.model.all))

    @property
    def groups(self):
        """All groups"""
        return (self.Group(dn, attrs) for dn, attrs in
                self.search(self.Group.model.all))

    def _watch_res_search_entry(self, dn, attrs, sync):
        """Process watch search entry"""
        user_objectClass = self.User.model.objectClass.lower()
        group_objectClass = self.Group.model.objectClass.lower()
        syncid = SyncId(sync.entryUUID)
        if sync.state == 'present':

            # Unchanged entry (identified only by UUID)
            logger.debug("Present entry %s", syncid)
            yield UnchangedSyncIds([syncid])

        elif sync.state == 'delete':

            # Deleted entry (identified only by UUID)
            logger.debug("Delete entry %s", syncid)
            yield DeletedSyncIds([syncid])

        else:

            # Modified or newly created entry (with UUID and DN)
            constructor = None
            attrs = LdapAttributeDict(attrs)
            for objectClass in attrs['objectclass']:
                objectClass = objectClass.decode().lower()
                if objectClass == user_objectClass:
                    constructor = self.User
                    break
                if objectClass == group_objectClass:
                    constructor = self.Group
                    break
            if constructor is None:
                raise LdapUnrecognisedEntryError(dn)
            entry = constructor(dn, attrs)
            if entry.uuid is None:
                entry.uuid = syncid
            elif entry.uuid != syncid:
                raise LdapSyncIdMismatchError(syncid, entry.uuid, dn)
            yield entry

        # Update cookie if applicable
        if sync.cookie is not None:
            yield SyncCookie(sync.cookie)

    @staticmethod
    def _watch_res_intermediate(sync):
        """Process watch intermediate result"""
        cookie = None
        if sync.newcookie is not None:

            # Updated cookie message
            cookie = sync.newcookie
            logger.debug("New cookie: %s", cookie)

        elif sync.refreshDelete is not None:

            # Delete phase complete
            cookie = sync.refreshDelete.get('cookie')
            done = sync.refreshDelete['refreshDone']
            logger.debug("Delete complete: done=%s cookie=%s", done, cookie)
            if done:
                yield RefreshComplete(autodelete=False)

        elif sync.refreshPresent is not None:

            # Present phase complete
            cookie = sync.refreshPresent.get('cookie')
            done = sync.refreshPresent['refreshDone']
            logger.debug("Present complete: done=%s cookie=%s", done, cookie)
            if done:
                yield RefreshComplete(autodelete=True)

        elif sync.syncIdSet is not None:

            # Synchronization identifier list
            cookie = sync.syncIdSet.get('cookie')
            delete = sync.syncIdSet['refreshDeletes']
            uuids = sync.syncIdSet['syncUUIDs']
            logger.debug("%s %d sync IDs: %s",
                         ("Delete" if delete else "Present"), len(uuids),
                         ", ".join(str(x) for x in uuids))
            cls = (DeletedSyncIds if delete else UnchangedSyncIds)
            syncids = cls([SyncId(x) for x in uuids])
            yield syncids

        else:

            # Unrecognised syncInfoValue
            raise LdapProtocolError("Unrecognised syncInfoValue")

        # Update cookie if applicable
        if cookie is not None:
            yield SyncCookie(cookie)

    @staticmethod
    def _watch_res_search_result(sync):
        """Process watch search result"""

        # Parse result
        cookie = sync.cookie
        delete = sync.refreshDeletes
        logger.debug("%s complete: cookie=%s",
                     ("Delete" if delete else "Present"), cookie)
        yield RefreshComplete(autodelete=not delete)

        # Update cookie if applicable
        if cookie is not None:
            yield SyncCookie(cookie)

    def watch(self, cookie=None, persist=True):
        """Watch for database changes"""

        # Issue request
        mode = 'refreshAndPersist' if persist else 'refreshOnly'
        cookie = str(cookie) if cookie is not None else None
        syncreq = SyncRequestControl(cookie=cookie, mode=mode)
        search = '(|%s%s)' % (self.User.model.all, self.Group.model.all)
        logger.debug("Searching in %s mode for %s", mode, search)
        msgid = self.ldap.search_ext(self.config.base,
                                     # pylint: disable=no-member
                                     ldap.SCOPE_SUBTREE, search, ['*', '+'],
                                     serverctrls=[syncreq])

        # Parse responses
        while True:
            res = LdapResult(*self.ldap.result4(msgid, all=0, add_ctrls=1,
                                                add_intermediates=1))
            rtype = res.type
            if rtype == ldap.RES_SEARCH_ENTRY:  # pylint: disable=no-member
                for dn, attrs, ctrls in res.data:
                    sync = next((ctrl for ctrl in ctrls if
                                 isinstance(ctrl, SyncStateControl)), None)
                    if sync is None:
                        raise LdapProtocolError("Missing syncStateControl")
                    yield from self._watch_res_search_entry(dn, attrs, sync)
            elif rtype == ldap.RES_INTERMEDIATE:  # pylint: disable=no-member
                sync = next((SyncInfoMessage(msg)
                             for rname, msg, ctrls in res.data
                             if rname == SyncInfoMessage.responseName), None)
                if sync is None:
                    raise LdapProtocolError("Missing syncInfoMessage")
                yield from self._watch_res_intermediate(sync)
            elif rtype == ldap.RES_SEARCH_RESULT:  # pylint: disable=no-member
                sync = next((ctrl for ctrl in res.ctrls if
                             isinstance(ctrl, SyncDoneControl)), None)
                if sync is None:
                    raise LdapProtocolError("Missing syncDoneControl")
                yield from self._watch_res_search_result(sync)
                break
            else:
                raise LdapProtocolError("Unrecognised message type")
