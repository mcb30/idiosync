"""FreeIPA user database"""

import logging
from .base import RefreshComplete
from .ldap import LdapBooleanAttribute, LdapEntryUuidAttribute, LdapModel
from .rfc2307 import Rfc2307User, Rfc2307Group, Rfc2307Config, Rfc2307Database

logger = logging.getLogger(__name__)


class IpaUser(Rfc2307User):
    """A FreeIPA user"""

    model = LdapModel('inetOrgPerson', 'uid',
                      lambda x: '(memberOf=%s)' % x.dn)

    disabled = LdapBooleanAttribute('nsAccountLock')
    uuid = LdapEntryUuidAttribute('nsUniqueId')

    @property
    def enabled(self):
        """User is enabled"""
        return not self.disabled


class IpaGroup(Rfc2307Group):
    """A FreeIPA group of users"""

    model = LdapModel('ipaUserGroup', 'cn', lambda x: '(member=%s)' % x.dn)

    uuid = LdapEntryUuidAttribute('nsUniqueId')


class IpaConfig(Rfc2307Config):
    """A FreeIPA user database configuration"""


class IpaDatabase(Rfc2307Database):
    """A FreeIPA user database"""

    Config = IpaConfig
    User = IpaUser
    Group = IpaGroup

    def watch(self, cookie=None, persist=True):
        """Watch for database changes"""
        incremental = cookie is not None
        for event in super().watch(cookie=cookie, persist=persist):
            if isinstance(event, RefreshComplete):
                if incremental and not persist:
                    # In refreshOnly mode with a request cookie,
                    # 389-ds-base will send any modified or deleted
                    # entries followed by a syncDoneControl with
                    # refreshDeletes omitted (thereby erroneously
                    # indicating that all unmentioned entries should
                    # be deleted).
                    #
                    # Work around this incorrect behaviour by assuming
                    # that an explicit deletion list will always be
                    # sent.
                    #
                    logger.warning("Assuming refreshDeletes=True intended")
                    event.autodelete = False
                elif persist and not incremental:
                    # In refreshAndPersist mode with no request
                    # cookie, 389-ds-base will send all existing
                    # entries followed by a syncInfoMessage of
                    # refreshDelete (thereby erroneously indicating
                    # that any unmentioned entries should not be
                    # deleted).
                    #
                    # Work around this incorrect behaviour by assuming
                    # that an initial content request always includes
                    # the full set of entries.
                    #
                    logger.warning("Assuming refreshPresent intended")
                    event.autodelete = True
            yield event
