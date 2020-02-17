"""Synchronization unit test common functionality"""

from ..base import database
from ..sync import synchronize
from .replay import ReplayedEntries, ReplayTestCase


class SynchronizerTestCase(ReplayTestCase):
    """Synchronization test case base class"""

    plugin = None

    def setUp(self):
        super().setUp()
        self.dst = self.plugin_database()
        self.dst.prepare()

    def tearDown(self):
        del self.dst
        super().tearDown()

    def plugin_database(self, **kwargs):
        """Construct plugin database"""
        return database(self.plugin, **kwargs)

    def ldap_sync(self, ldif):
        """Synchronize database from LDIF file"""
        with self.ldap_patch(ldif) as entries:
            synchronize(self.src, self.dst)
        return ReplayedEntries(
            users={k: self.dst.User.find_match(v)
                   for k, v in entries.users.items()},
            groups={k: self.dst.Group.find_match(v)
                    for k, v in entries.groups.items()},
        )

    def test_empty(self):
        """Test that initial database state is valid but empty"""
        self.assertEqual(list(self.dst.users), [])
        self.assertEqual(list(self.dst.groups), [])

    def test_create_users(self):
        """Test create-users.ldif"""
        entries = self.ldap_sync('create-users.ldif')
        self.assertEqual(len(entries.users), 2)
