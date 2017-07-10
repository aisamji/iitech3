"""Tests to confirm the operation of the CLI."""
import os
import unittest
from unittest import mock
import pasteboard
import main
import cache
import document


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


class ReviewTests(unittest.TestCase):
    """Confirm the operation of the review command."""

    def setUp(self):
        """Prepare the environment."""
        self._document = mock.MagicMock(document.Document)
        self._document.__str__.return_value = '<html></html>'
        document_patcher = mock.patch('main.document.Document.__new__', return_value=self._document)
        self.addCleanup(document_patcher.stop)
        self.mock_document = document_patcher.start()

    def test_review_pasteboard(self):
        """Confirm that the code to be reviewed is retrieved from the pasteboard and put back on to it."""
        code = '<html></html>'
        pasteboard.set(code)
        main.main('review -p'.split())

        self.mock_document.assert_called_with(document.Document, code)
        self.assertTrue(self._document.review.called, 'The document should be reviewed.')
        self.assertEqual(code, pasteboard.get(),
                         'The reviewed document should be put back on the pasteboard.')

    def test_review_file(self):
        """Confirm that the code to be reviewed is read from a file and written back to it."""
        code = '<html></html>'
        with open('fake.txt', 'w') as file:
            file.write(code)
        self.addCleanup(os.remove, 'fake.txt')
        main.main('review fake.txt'.split())

        with open('fake.txt', 'r') as file:
            data = file.read()
        self.mock_document.assert_called_with(document.Document, code)
        self.assertTrue(self._document.review.called, 'The document should be reviewed.')
        self.assertEqual(code, data,
                         'The reviewed document should be written back to the file.')
