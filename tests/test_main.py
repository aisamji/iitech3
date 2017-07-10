"""Tests to confirm the operation of the CLI."""
import unittest
from unittest import mock
import main
import cache


class LookupTests(unittest.TestCase):
    """A test suite to confirm the operation of the lookup command."""

    def setUp(self):
        """Prepare the environment."""
        self._cache = mock.MagicMock(cache.Cache)
        self._cache.get_email.return_value = cache.InfoHolder(address='ali.samji@outlook.com',
                                                              is_valid=True,
                                                              reason='accepted_email')
        self._cache.get_webpage.return_value = cache.InfoHolder(url='https://www.google.com',
                                                                status=200)
        factory_patcher = mock.patch('main.cache.get_default',
                                     return_value=self._cache)
        self.addCleanup(factory_patcher.stop)
        self.addCleanup(self._cache.reset_mock)
        self.mock_factory = factory_patcher.start()

    def test_no_opt_email(self):
        """Confirm that the lookup email command with no options calls the correct methods."""
        main.main('lookup email ali.samji@outlook.com'.split())

        self._cache.lookup_email.assert_not_called()
        self._cache.get_email.assert_called_with('ali.samji@outlook.com', nolookup=False)

    def test_forced_email(self):
        """Confirm that the lookup email command with a forced lookup calls the correct methods."""
        main.main('lookup email --forced ali.samji@outlook.com'.split())

        self._cache.lookup_email.assert_called_with('ali.samji@outlook.com')
        self._cache.get_email.assert_called_with('ali.samji@outlook.com', nolookup=False)

    def test_cached_email(self):
        """Confirm that the lookup email command with a cached-only query calls the correct methods."""
        main.main('lookup email --cached ali.samji@outlook.com'.split())

        self._cache.lookup_email.assert_not_called()
        self._cache.get_email.assert_called_with('ali.samji@outlook.com', nolookup=True)

    def test_no_opt_webpage(self):
        """Confirm that the lookup webpage command with no options calls the correct methods."""
        main.main('lookup webpage https://www.google.com'.split())

        self._cache.lookup_webpage.assert_not_called()
        self._cache.get_webpage.assert_called_with('https://www.google.com', nolookup=False)

    def test_forced_webpage(self):
        """Confirm that the lookup webpage command with a forced lookup calls the correct methods."""
        main.main('lookup webpage --forced https://www.google.com'.split())

        self._cache.lookup_webpage.assert_called_with('https://www.google.com')
        self._cache.get_webpage.assert_called_with('https://www.google.com', nolookup=False)

    def test_cached_webpage(self):
        """Confirm that the lookup webpage command with a cached-only query calls the correct methods."""
        main.main('lookup webpage --cached https://www.google.com'.split())

        self._cache.lookup_webpage.assert_not_called()
        self._cache.get_webpage.assert_called_with('https://www.google.com', nolookup=True)
