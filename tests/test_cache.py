"""Tests to ensure correct operation of the cache."""
import os
import unittest
import sqlite3
import cache


class DatabaseTests(unittest.TestCase):
    """A test suite to confirm the communication of the caching database."""

    def setUp(self):
        """Mock out the requests interface."""
        db_dir = '../data'
        self.db_path = os.path.join(db_dir, 'cache.db')
        self.addCleanup(os.rmdir, db_dir)
        self.addCleanup(os.remove, self.db_path)
        self._cache = cache.Cache(self.db_path)

    def test_database_format(self):
        """Confirm the format of the caching database."""
        connection = sqlite3.connect(self.db_path)
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = list(zip(*tables))[0]
        self.assertTrue('webpages' in tables and 'emails' in tables and len(tables) == 2,
                        'Too many tables: {!s:}'.format(tables))

        webpage_cols = connection.execute("PRAGMA table_info(webpages)").fetchall()
        email_cols = connection.execute("PRAGMA table_info(emails)").fetchall()
        self.assertTrue('url' == webpage_cols[0][1] and
                        'status' == webpage_cols[1][1] and
                        'last_lookup' == webpage_cols[2][1] and len(webpage_cols) == 3,
                        'Too many columns in webpages: {!s:}'.format(webpage_cols))
        self.assertTrue('address' == email_cols[0][1] and
                        'is_valid' == email_cols[1][1] and
                        'reason' == email_cols[2][1] and
                        'last_lookup' == email_cols[3][1] and len(email_cols) == 4,
                        'Too many columns in emails: {!s:}'.format(email_cols))
