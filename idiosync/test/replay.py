"""LDIF replay unit test common functionality"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict
from unittest.mock import patch
import ldap
from ..base import User, Group
from ..freeipa import IpaDatabase
from ..ldap import LdapResult
from .common import TestCase


@dataclass
class ReplayedEntries:
    """Summary of replayed database entries"""

    users: Dict[str, User] = field(default_factory=dict)
    groups: Dict[str, Group] = field(default_factory=dict)

    def record(self, entry):
        """Record database entry"""
        if isinstance(entry, User):
            self.users[entry.key] = entry
        elif isinstance(entry, Group):
            self.groups[entry.key] = entry


class ReplayTestCase(TestCase):
    """LDIF replay test case base class"""

    def setUp(self):
        super().setUp()
        self.src = self.ldap_database()

    def tearDown(self):
        del self.src
        super().tearDown()

    @staticmethod
    def ldap_database():
        """Construct LDAP database"""
        with patch.object(ldap, 'initialize', autospec=True):
            return IpaDatabase()

    def ldap_watch_search(self, ldif):
        """Read all LDAP trace events from LDIF file"""
        with self.resource_textio(ldif) as fh:
            yield from LdapResult.readall(fh)

    def ldap_watch(self, entries):
        """Record all LDAP entries"""
        def watch_and_record(*args, watch=self.src.watch, **kwargs):
            for entry in watch(*args, **kwargs):
                entries.record(entry)
                yield entry
        return watch_and_record

    @contextmanager
    def ldap_patch(self, ldif):
        """Patch LDAP source to replay LDAP trace events from LDIF file"""
        entries = ReplayedEntries()
        with patch.object(self.src, 'watch', autospec=True,
                          side_effect=self.ldap_watch(entries)):
            with patch.object(self.src, '_watch_search', autospec=True,
                              return_value=self.ldap_watch_search(ldif)):
                yield entries

    def ldap_replay(self, ldif):
        """Replay LDAP trace events from LDIF file"""
        with self.ldap_patch(ldif) as entries:
            list(self.src.watch())
        return entries
