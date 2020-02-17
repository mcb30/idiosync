"""Unit test common functionality"""

from io import TextIOWrapper
import unittest
import pkg_resources


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
