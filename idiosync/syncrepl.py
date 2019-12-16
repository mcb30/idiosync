"""Workarounds for bugs in pyldap's syncrepl module"""

from uuid import UUID
import ldap.syncrepl
from pyasn1.codec.ber import decoder

try:
    # pylint: disable=no-member
    SyncInfoValue = ldap.syncrepl.SyncInfoValue
except AttributeError:
    # pylint: disable=no-member
    SyncInfoValue = ldap.syncrepl.syncInfoValue


class SyncInfoMessage:
    """A syncInfoMessage intermediate message"""
    # pylint: disable=no-member

    responseName = ldap.syncrepl.SyncInfoMessage.responseName

    def __init__(self, encodedMessage):
        d = decoder.decode(encodedMessage, asn1Spec=SyncInfoValue())
        self.newcookie = None
        self.refreshDelete = None
        self.refreshPresent = None
        self.syncIdSet = None

        attr = d[0].getName()
        comp = d[0].getComponent()

        if attr == 'newcookie':
            self.newcookie = str(comp)
            return

        val = {}

        cookie = comp.getComponentByName('cookie')
        if cookie.hasValue():
            val['cookie'] = str(cookie)

        if attr.startswith('refresh'):
            val['refreshDone'] = bool(comp.getComponentByName('refreshDone'))
        elif attr == 'syncIdSet':
            uuids = []
            ids = comp.getComponentByName('syncUUIDs')
            for i in range(len(ids)):
                uuid = UUID(bytes=bytes(ids.getComponentByPosition(i)))
                uuids.append(str(uuid))
            val['syncUUIDs'] = uuids
            val['refreshDeletes'] = bool(
                comp.getComponentByName('refreshDeletes')
            )

        setattr(self, attr, val)
