"""SQLAlchemy test functionality"""

from contextlib import closing
from .sync import SynchronizerTestCase


class SqlTestCase(SynchronizerTestCase):
    """SQLAlchemy test case base class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = cls.resource_text('%s.sql' % cls.plugin)

    def plugin_database(self, **kwargs):
        dst = super().plugin_database(uri='sqlite://', **kwargs)
        with closing(dst.engine.raw_connection()) as conn:
            conn.cursor().executescript(self.schema)
        return dst

    def tearDown(self):
        self.dst.engine.dispose()
        super().tearDown()
