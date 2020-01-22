"""Test LDIF replay"""

from idiosync.freeipa import IpaDatabase
from idiosync.test.common import TestCase
from idiosync.base import User


class TestReplay(TestCase):
    """Test LDIF replay"""

    def test_create_users(self):
        """Test create-users.ldif"""
        with self.patch_ldif('create-users.ldif'):
            entries = list(IpaDatabase().watch())
        users = {x.key: x for x in entries if isinstance(x, User)}
        self.assertEqual(users.keys(), {'alice', 'bob'})
        self.assertEqual(users['alice'].surname, "Archer")
        self.assertEqual(users['alice'].commonName, "Alice Archer")
        self.assertEqual(users['bob'].givenName, "Bob")
        self.assertEqual(users['bob'].surname, "Baker")

    def test_modify_users(self):
        """Test modify-users.ldif"""
        with self.patch_ldif('modify-users.ldif'):
            entries = list(IpaDatabase().watch())
        users = {x.key: x for x in entries if isinstance(x, User)}
        self.assertEqual(users.keys(), {'bob'})
        self.assertEqual(users['bob'].givenName, "Bobby")
