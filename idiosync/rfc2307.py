"""RFC2307 LDAP user database"""

from .ldap import (LdapNumericAttribute, LdapStringAttribute, LdapSearch,
                   LdapUser, LdapGroup, LdapConfig, LdapDatabase)


class Rfc2307User(LdapUser):
    """An RFC2307 user"""

    search = LdapSearch('posixAccount', 'uid',
                        lambda group: ('(|%s)' %
                                       ''.join('(uid=%s)' % uid
                                               for uid in group.memberUid)))

    gidNumber = LdapNumericAttribute('gidNumber')
    uidNumber = LdapNumericAttribute('uidNumber')
    uid = LdapStringAttribute('uid')

    name = uid


class Rfc2307Group(LdapGroup):
    """An RFC2307 group"""

    search = LdapSearch('posixGroup', 'cn', lambda x: '(memberUid=%s)' % x.uid)

    gidNumber = LdapNumericAttribute('gidNumber')
    memberUid = LdapStringAttribute('memberUid', multi=True)


class Rfc2307Config(LdapConfig):
    """An RFC2307 user database configuration"""
    # pylint: disable=too-few-public-methods
    pass


class Rfc2307Database(LdapDatabase):
    """An RFC2307 user database"""

    Config = Rfc2307Config
    User = Rfc2307User
    Group = Rfc2307Group
