"""Dummy user database"""

import uuid
from .base import WritableGroup

NAMESPACE_DUMMY = uuid.UUID('c5dd5cb8-b889-431e-8426-81297a053894')


class DummyGroup(WritableGroup):
    """A dummy group

    Some user databases (such as MediaWiki) have no table for group
    definitions.  In such databases, a group exists if and only if it
    has members; there is no separate concept of group existence.
    """
    # pylint: disable=abstract-method

    key = None

    def __init__(self, key):
        self.key = key

    @property
    def uuid(self):
        """Permanent identifier for this entry

        A dummy permanent identifier is generated as a UUID based on
        the group key.  This provides a viable unique identifier, with
        the caveat that a rename will be treated as a deletion and an
        unrelated creation.
        """
        return uuid.uuid5(NAMESPACE_DUMMY, self.key)

    @property
    def syncid(self):
        """Synchronization identifier"""
        return None

    @syncid.setter
    def syncid(self, value):
        """Set synchronization identifier"""
        pass

    @classmethod
    def find(cls, key):
        """Look up user database entry"""
        return cls(key)

    @classmethod
    def find_syncid(cls, syncid):
        """Look up user database entry by synchronization identifier"""
        return None

    @classmethod
    def create(cls):
        """Create new user database entry"""
        return cls(None)

    @classmethod
    def delete(cls, syncids):
        """Delete all of the specified entries"""
        pass

    @classmethod
    def prune(cls, syncids):
        """Delete all synchronized entries except the specified entries"""
        pass
