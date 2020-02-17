"""Test Request Tracker database"""

import idiosync.test


class RequestTrackerTestCase(idiosync.test.SqlTestCase):
    """Request Tracker database tests"""

    plugin = 'requesttracker'
