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
        """Confirm the review feature returns a document with the proper corrections."""
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
        self.assertIsNotNone(re.search(r'<a href="https://www\.shitface\.org" target="_blank">\s*\*BROKEN 410\*\s*TELL ME IM BROKEN!\s*</a>', str(apple)),
                             'https://www.shitface.org should be marked broken and the target should be fixed.')
        self.assertIsNotNone(re.search(r'<a href="https://journeyforhealth\.org" target="_blank">\s*CHANGE ME!\s*</a>', str(apple)),
                             'Additional trackers should be removed.')
        self.assertIsNotNone(re.search(r'<a href="##TRACKCLICK##https://www\.google\.com" target="_blank">\s*DONT TOUCH ME!\s*</a>', str(apple)),
                             'A link should not be touched if it is correct.')
