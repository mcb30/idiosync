"""FreeIPA user database"""

from .ldap import LdapUuidAttribute, LdapSearch
from .rfc2307 import Rfc2307User, Rfc2307Group, Rfc2307Config, Rfc2307Database


class IpaUser(Rfc2307User):
    """A FreeIPA user"""

    search = LdapSearch('inetOrgPerson', 'uid',
                        lambda x: '(memberOf=%s)' % x.dn)

    uuid = LdapUuidAttribute('ipaUniqueID')


class IpaGroup(Rfc2307Group):
    """A FreeIPA group of users"""

    search = LdapSearch('ipaUserGroup', 'cn', lambda x: '(member=%s)' % x.dn)

    uuid = LdapUuidAttribute('ipaUniqueID')


class IpaConfig(Rfc2307Config):
    """A FreeIPA user database configuration"""
    # pylint: disable=too-few-public-methods
    pass


class IpaDatabase(Rfc2307Database):
    """A FreeIPA user database"""

    Config = IpaConfig
    User = IpaUser
    Group = IpaGroup
