"""Test MediaWiki database"""

import idiosync.test


class MediaWikiTestCase(idiosync.test.SqlTestCase):
    """MediaWiki database tests"""

    plugin = 'mediawiki'
