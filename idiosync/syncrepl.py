"""Workarounds for bugs in pyldap's syncrepl module"""

import ldap.syncrepl
from pyasn1.codec.ber import decoder

try:
    SyncInfoValue = ldap.syncrepl.SyncInfoValue
except AttributeError:
    SyncInfoValue = ldap.syncrepl.syncInfoValue


class SyncInfoMessage(object):
    """A syncInfoMessage intermediate message"""
    # pylint: disable=too-few-public-methods, no-member

    responseName = ldap.syncrepl.SyncInfoMessage.responseName

    def __init__(self, encodedMessage):
        d = decoder.decode(encodedMessage, asn1Spec=SyncInfoValue())
        self.newcookie = None
        self.refreshDelete = None
        self.refreshPresent = None
        self.syncIdSet = None
        setattr(self, d[0].getName(), dict(d[0].getComponent()))
