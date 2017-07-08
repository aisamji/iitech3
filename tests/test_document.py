"""Tests for the document class."""
import unittest
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
                <!-- External links -->
                <a href="">REMOVE ME!</a>
                <a href="##TRACKCLICK##">REMOVE ME!</a>
                <a href="https://www.shitface.org" target="_self">TELL ME IM BROKEN!</a>
                <a href="http://www.ismailiinsight.org/enewsletterpro/t.aspx?url=https%3A%2F%2Fjourneyforhealth.org"
                   target="_self">CHANGE ME!</a>
                <a href="https://www.google.com" target="_blank">DONT TOUCH ME!</a>
            </body>
            """

        goal = ('<html>\n <head>\n </head>\n <body>\n  <!-- External links -->\n'
                '  <a href="https://www.shitface.org" target="_blank">\n   *BROKEN 410*\n   TELL ME IM BROKEN!\n  </a>\n'
                '  <a href="https://journeyforhealth.org" target="_blank">\n   CHANGE ME!\n  </a>\n'
                '  <a href="https://www.google.com" target="_blank">\n   DONT TOUCH ME!\n  </a>\n'
                ' </body>\n</html>')

        apple = document.Document(markup)
        apple.review()

        self.assertEqual(goal, str(apple), 'The html code should be fixed to match the specified goal.')
