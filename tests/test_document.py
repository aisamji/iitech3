"""Tests for the document class."""
import unittest
import re
import remocks
import cache
import document


class DocumentTests(unittest.TestCase):
    """Test suite for the Document class."""

    @unittest.mock.patch('document.cache.requests', remocks)
    @unittest.mock.patch('document.cache.get_default', return_value=cache.Cache(':memory:'))
    def test_external_link_review(self, mock_default_cache):
        """Confirm the review feature correctly fixes external links."""
        markup = """
            <body>
                <a href="">REMOVE ME!</a>
                <a href="##TRACKCLICK##">REMOVE ME!</a>
                <a href="https://www.shitface.org" target="_self">TELL ME IM BROKEN!</a>
                <a href="http://www.ismailiinsight.org/enewsletterpro/t.aspx?url=https%3A%2F%2Fjourneyforhealth.org"
                   target="_blank">CHANGE ME!</a>
                <a href="##TRACKCLICK##https://www.google.com" target="_blank">DONT TOUCH ME!</a>
            </body>
            """

        apple = document.Document(markup)
        apple.review()

        self.assertIsNone(re.search(r'<a href="">\s*REMOVE ME!\s*</a>', str(apple)),
                          'The blank link should be removed.')
        self.assertIsNone(re.search(r'<a href="##TRACKCLICK##">\s*REMOVE ME!\s*</a>', str(apple)),
                          'The useless tracker should be removed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="https://www\.shitface\.org" target="_blank">\s*\*BROKEN 410\*\s*TELL ME IM BROKEN!\s*</a>', # noqa
                                 str(apple)),
                             'https://www.shitface.org should be marked broken and the target should be fixed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="https://journeyforhealth\.org" target="_blank">\s*CHANGE ME!\s*</a>',
                                 str(apple)),
                             'Additional trackers should be removed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="##TRACKCLICK##https://www\.google\.com" target="_blank">\s*DONT TOUCH ME!\s*</a>', # noqa
                                 str(apple)),
                             'A link should not be touched if it is correct.')

    def test_internal_link_review(self):
        """Confirm the review feature correctly fixes internal links."""
        markup = """
            <body>
                <a name="northpole">WELCOME TO THE NORTHPOLE</a>
                <a href="#northpole">WHERE IS SANTA CLAUS</a>
                <a href="#waldo">WHERE IS WALDO</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        self.assertIsNotNone(re.search(
                                 r'<a name="northpole">\s*WELCOME TO THE NORTHPOLE\s*</a>',
                                 str(apple)),
                             'Anchors should not be touched, only counted.')
        self.assertIsNotNone(re.search(
                                 r'<a href="#northpole">\s*WHERE IS SANTA CLAUS\s*</a>',
                                 str(apple)),
                             'A link to an existing anchor should not be changed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="#waldo">\s*\*NOTFOUND waldo\*\s*WHERE IS WALDO\s*</a>',
                                 str(apple)),
                             'A non-existent link should be marked.')

    @unittest.mock.patch('document.cache.requests', remocks)
    @unittest.mock.patch('document.cache.get_default', return_value=cache.Cache(':memory:'))
    def test_email_review(self, mock_default_cache):
        """Confirm the review feature correctly fixes emails."""
        markup = """
            <body>
                <a href="mailto:%20ali.samji@outlook.com">EXTRA SPACE</a>
                <a href="mailto:richard@quickemailverification.com">FAKE EMAIL</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        self.assertIsNotNone(re.search(
                                 r'<a href="mailto:ali\.samji@outlook\.com">\s*EXTRA SPACE\s*</a>',
                                 str(apple)),
                             'Extra spaces should be stripped and the resulting email verified.')
        self.assertIsNotNone(re.search(
                                 r'<a href="mailto:richard@quickemailverification\.com">\s*\*BAD rejected_email\*\s*FAKE EMAIL\s*</a>', # noqa
                                 str(apple)),
                             'Bad emails should be marked as such.')
