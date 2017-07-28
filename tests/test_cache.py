"""Tests to ensure correct operation of the cache."""
import os
import unittest
import datetime
import cache
import exceptions
import mklite3
import mocktime
import remocks


class BranchTests(unittest.TestCase):
    """A test suite to confirm the branching paths of the cache object."""

    def setUp(self):
        """Mock out all external interfaces and create the cache object."""
        sqlite3_patcher = unittest.mock.patch('cache.sqlite3', mklite3)
        datetime_patcher = unittest.mock.patch('cache.datetime', mocktime)
        os_patcher = unittest.mock.patch('cache.os')
        self.addCleanup(sqlite3_patcher.stop)
        self.addCleanup(datetime_patcher.stop)
        self.addCleanup(os_patcher.stop)
        sqlite3_patcher.start()
        datetime_patcher.start()
        os_patcher.start()

        self._cache = cache.Cache(':memory:')

    def test_cache_miss_nolookup(self):
        """Confirm a CacheMissException is raised when online lookups are disabled."""
        self.assertRaises(exceptions.CacheMissException, self._cache.get_webpage,
                          'https://www.techcrunch.com', nolookup=True)
        self.assertRaises(exceptions.CacheMissException, self._cache.get_email,
                          'ali.samji@outlook.com', nolookup=True)

    @unittest.mock.patch.object(cache.Cache, 'lookup_webpage')
    @unittest.mock.patch.object(cache.Cache, 'lookup_email')
    def test_replace_old(self, mock_email, mock_webpage):
        """Confirm that old cache values are replaced."""
        self._cache.get_webpage('https://www.apple.com')
        self._cache.get_email('aisamji09@gmail.com')

        self._cache.lookup_webpage.assert_called_with('https://www.apple.com')
        self._cache.lookup_email.assert_called_with('aisamji09@gmail.com')

    @unittest.mock.patch('cache.requests', remocks)
    def test_cache_miss_lookup(self):
        """Confirm that the value is retrieved from online when it is not in the cache."""
        self._cache.get_webpage('https://www.google.com')
        remocks.get.assert_called_with('https://www.google.com')

        self._cache.get_email('richard@quickemailverification.com')
        remocks.get.assert_called_with(cache.Cache.EMAIL_API_ENDPOINT.format(
            'richard@quickemailverification.com'))

    @unittest.mock.patch('cache.requests', remocks)
    def test_url_gone(self):
        """Confirm that a url that is gone returns 410."""
        info = self._cache.get_webpage('https://www.jubileeconcerts.ismaili')
        self.assertEqual(410, info.status,
                         'The status should be 410 if the webpage does not exist.')


class DatabaseTests(unittest.TestCase):
    """A test suite to confirm the communication of the caching database."""

    def setUp(self):
        """Create the cache object before each test."""
        db_dir = '../data'
        self.db_path = os.path.join(db_dir, 'cache.db')
        self.addCleanup(os.rmdir, db_dir)
        self.addCleanup(os.remove, self.db_path)
        self._cache = cache.Cache(self.db_path)

    def test_schema(self):
        """Confirm the format of the caching database."""
        tables = self._cache._database.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = list(zip(*tables))[0]
        self.assertTrue('webpages' in tables and 'emails' in tables and len(tables) == 2,
                        'Too many tables: {!s:}'.format(tables))

        webpage_cols = self._cache._database.execute("PRAGMA table_info(webpages)").fetchall()
        webpage_cols = list(zip(*webpage_cols))[1]
        email_cols = self._cache._database.execute("PRAGMA table_info(emails)").fetchall()
        email_cols = list(zip(*email_cols))[1]
        self.assertEqual(('url', 'status', 'last_lookup'), webpage_cols,
                         'Too many columns in webpages: {!s:}'.format(webpage_cols))
        self.assertEqual(('address', 'is_valid', 'reason', 'last_lookup'), email_cols,
                         'Too many columns in emails: {!s:}'.format(email_cols))

    def test_data_round_trip(self):
        """Confirm the types of the data on round trip to/from the database."""
        self._cache.set_email('ali.samji@outlook.com', False)
        info = self._cache.get_email('ali.samji@outlook.com', nolookup=True)
        self.assertEqual(type(info.address), str, 'The address should be of type str.')
        self.assertEqual(type(info.is_valid), bool, 'The validity should be of type bool.')
        self.assertEqual(type(info.reason), str, 'The reason should be of type str.')
        self.assertEqual(type(info.last_lookup), datetime.datetime,
                         'The lookup time should be a datetime object.')
        self.assertEqual(info.address, 'ali.samji@outlook.com', 'The address should be ali.samji@outlook.com')
        self.assertEqual(info.is_valid, False, 'The validity should be False.')
