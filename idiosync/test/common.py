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

    @classmethod
    def resource_package(cls, name):
        """Identify most specific package containing a named resource"""
        for subcls in cls.__mro__:
            if pkg_resources.resource_exists(subcls.__module__, name):
                return subcls.__module__
            if subcls == TestCase:
                break
        raise KeyError("Missing resource '%s'" % name)

    @classmethod
    def resource_string(cls, name):
        """Get package resource content as (byte) string"""
        return pkg_resources.resource_string(cls.resource_package(name), name)

    @classmethod
    def resource_stream(cls, name):
        """Get package resource content as (binary) file-like object"""
        return pkg_resources.resource_stream(cls.resource_package(name), name)

    @classmethod
    def resource_text(cls, name):
        """Get package resource content as (text) string"""
        return cls.resource_string(name).decode()

    @classmethod
    def resource_textio(cls, name):
        """Get package resource content as (text) file-like object"""
        return TextIOWrapper(cls.resource_stream(name))

    @classmethod
    def readall(cls, ldif):
        """Read all trace events from LDIF file"""
        with cls.resource_textio(ldif) as fh:
            yield from LdapResult.readall(fh)

    @classmethod
    @contextmanager
    def patch_ldif(cls, ldif):
        """Patch LDAP database to return trace events from LDIF file"""
        with patch.object(ldap, 'initialize', autospec=True):
            with patch.object(LdapDatabase, '_watch_search', autospec=True,
                              return_value=cls.readall(ldif)):
                yield
