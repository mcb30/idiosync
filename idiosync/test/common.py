"""Unit test common functionality"""

from contextlib import contextmanager
from io import TextIOWrapper
import unittest
from unittest.mock import patch
import pkg_resources
import ldap
from ..ldap import LdapResult, LdapDatabase


class TestCase(unittest.TestCase):
    """Test case base class"""

    @staticmethod
    def readall(ldif):
        """Read all trace events from LDIF file"""
        with pkg_resources.resource_stream(__name__, ldif) as binfh:
            with TextIOWrapper(binfh) as fh:
                yield from LdapResult.readall(fh)

    @classmethod
    @contextmanager
    def patch_ldif(cls, ldif):
        """Patch LDAP database to return trace events from LDIF file"""
        with patch.object(ldap, 'initialize', autospec=True):
            with patch.object(LdapDatabase, '_watch_search', autospec=True,
                              return_value=cls.readall(ldif)):
                yield
