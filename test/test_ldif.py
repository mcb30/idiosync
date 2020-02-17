"""Test LDIF replay"""

from idiosync.test import ReplayTestCase


class TestReplay(ReplayTestCase):
    """Test LDIF replay"""

    def test_create_users(self):
        """Test create-users.ldif"""
        entries = self.ldap_replay('create-users.ldif')
        self.assertEqual(entries.users.keys(), {'alice', 'bob'})
        self.assertEqual(entries.users['alice'].surname, "Archer")
        self.assertEqual(entries.users['alice'].commonName, "Alice Archer")
        self.assertEqual(entries.users['bob'].givenName, "Bob")
        self.assertEqual(entries.users['bob'].surname, "Baker")

    def test_modify_users(self):
        """Test modify-users.ldif"""
        entries = self.ldap_replay('modify-users.ldif')
        self.assertEqual(entries.users.keys(), {'bob'})
        self.assertEqual(entries.users['bob'].givenName, "Bobby")
