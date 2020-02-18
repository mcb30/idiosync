"""Synchronization unit test common functionality"""

from ..plugins import plugins
from ..sync import synchronize
from .replay import ReplayedEntries, ReplayTestCase


class SynchronizerTestCase(ReplayTestCase):
    """Synchronization test case base class"""
    # pylint: disable=too-many-public-methods

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
        return plugins[self.plugin](**kwargs)

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

    def assertAttribute(self, Entry, entry, attr, value, multi=False):
        """Assert that entry attribute value is correct"""
        # pylint: disable=too-many-arguments
        self.assertIsInstance(entry, Entry)
        if hasattr(Entry, attr):
            if getattr(Entry, attr).multi and not multi:
                self.assertEqual(getattr(entry, attr), [value])
            elif multi and not getattr(Entry, attr).multi:
                self.assertEqual(getattr(entry, attr), value[0])
            else:
                self.assertEqual(getattr(entry, attr), value)

    def assertUserCommonName(self, entry, value):
        """Assert that user commonName attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'commonName', value)

    def assertUserDisplayName(self, entry, value):
        """Assert that user displayName attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'displayName', value)

    def assertUserEmployeeNumber(self, entry, value):
        """Assert that user employeeNumber attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'employeeNumber', value)

    def assertUserGivenName(self, entry, value):
        """Assert that user givenName attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'givenName', value)

    def assertUserInitials(self, entry, value):
        """Assert that user initials attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'initials', value)

    def assertUserMail(self, entry, value):
        """Assert that user mail attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'mail', value, multi=True)

    def assertUserMobile(self, entry, value):
        """Assert that user mobile attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'mobile', value, multi=True)

    def assertUserSurname(self, entry, value):
        """Assert that user surname attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'surname', value)

    def assertUserTelephoneNumber(self, entry, value):
        """Assert that user telephoneNumber attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'telephoneNumber', value)

    def assertUserTitle(self, entry, value):
        """Assert that user title attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'title', value)

    def assertUserUid(self, entry, value):
        """Assert that user uid attribute value is correct"""
        self.assertAttribute(self.dst.User, entry, 'uid', value)

    def assertGroupCommonName(self, entry, value):
        """Assert that group commonName attribute value is correct"""
        self.assertAttribute(self.dst.Group, entry, 'commonName', value)

    def assertGroupDescription(self, entry, value):
        """Assert that group description attribute value is correct"""
        self.assertAttribute(self.dst.Group, entry, 'description', value)

    def assertEnabled(self, Entry, entry, enabled):
        """Assert that entry is enabled (or disabled)"""
        self.assertIsInstance(entry, Entry)
        self.assertEqual(entry.enabled, enabled)

    def assertUserEnabled(self, entry):
        """Assert that user is enabled"""
        self.assertEnabled(self.dst.User, entry, True)

    def assertUserDisabled(self, entry):
        """Assert that user is disabled"""
        self.assertEnabled(self.dst.User, entry, False)

    def assertGroupEnabled(self, entry):
        """Assert that group is enabled"""
        self.assertEnabled(self.dst.Group, entry, True)

    def assertGroupDisabled(self, entry):
        """Assert that group is disabled"""
        self.assertEnabled(self.dst.Group, entry, False)

    def test_empty(self):
        """Test that initial database state is valid but empty"""
        self.assertEqual(list(self.dst.users), [])
        self.assertEqual(list(self.dst.groups), [])

    def test_create_users(self):
        """Test create-users.ldif"""
        entries = self.ldap_sync('create-users.ldif')
        self.assertEqual(len(entries.users), 2)
        self.assertUserCommonName(entries.users['alice'], "Alice Archer")
        self.assertUserDisplayName(entries.users['bob'], "Bob Baker")
        self.assertUserMail(entries.users['alice'], ["alice@example.org"])
        self.assertUserSurname(entries.users['alice'], "Archer")
        self.assertUserUid(entries.users['bob'], "bob")
        self.assertUserEnabled(entries.users['alice'])
