"""Tests for the document class."""
import unittest
import re
import bs4
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
        code = str(apple)

        self.assertIsNone(re.search(r'<a href="">\s*REMOVE ME!\s*</a>', str(apple)),
                          'The blank link should be removed.')
        self.assertIsNone(re.search(r'<a href="##TRACKCLICK##">\s*REMOVE ME!\s*</a>', str(apple)),
                          'The useless tracker should be removed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="https://www\.shitface\.org" target="_blank">\s*\*BROKEN 410\*\s*TELL ME IM BROKEN!\s*</a>', # noqa
                                 code),
                             'https://www.shitface.org should be marked broken and the target should be fixed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="https://journeyforhealth\.org" target="_blank">\s*CHANGE ME!\s*</a>',
                                 code),
                             'Additional trackers should be removed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="##TRACKCLICK##https://www\.google\.com" target="_blank">\s*DONT TOUCH ME!\s*</a>', # noqa
                                 code),
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
        code = str(apple)

        self.assertIsNotNone(re.search(
                                 r'<a name="northpole">\s*WELCOME TO THE NORTHPOLE\s*</a>',
                                 code),
                             'Anchors should not be touched, only counted.')
        self.assertIsNotNone(re.search(
                                 r'<a href="#northpole">\s*WHERE IS SANTA CLAUS\s*</a>',
                                 code),
                             'A link to an existing anchor should not be changed.')
        self.assertIsNotNone(re.search(
                                 r'<a href="#waldo">\s*\*MISSING waldo\*\s*WHERE IS WALDO\s*</a>',
                                 code),
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
        code = str(apple)

        self.assertIsNotNone(re.search(
                                 r'<a href="mailto:ali\.samji@outlook\.com">\s*EXTRA SPACE\s*</a>',
                                 code),
                             'Extra spaces should be stripped and the resulting email verified.')
        self.assertIsNotNone(re.search(
                                 r'<a href="mailto:richard@quickemailverification\.com">\s*\*INVALID rejected_email\*\s*FAKE EMAIL\s*</a>', # noqa
                                 code),
                             'Bad emails should be marked as such.')


class RepairTests(unittest.TestCase):
    """Test suite for the repair function."""

    def setUp(self):
        """Prepare the environment."""
        pass

    def test_do_nothing(self):
        """Confirm whether the code is not modified unnecessarily."""
        markup = """
            <html>
                <head>
                </head>
                <body>
                    <div style="background-color: #595959;">
                        <a href="https://www.ismailiinsight.com">NOTHING SHOULD BE CHANGED</a>
                    </div>
                </body>
            </html>
        """

        apple = document.Document(markup)
        apple.repair()

        banana = bs4.BeautifulSoup(markup, 'html5lib')
        self.assertEqual(banana, apple._data, 'The code should not be changed if it is already correct.')

    def test_remove_styles(self):
        """Confirm that the code is stripped of all style tags."""
        markup = """
            <html>
                <head>
                    <style>THIS IS VALID CSS</style>
                    <style>THIS IS ALSO VALID CSS</style>
                    <style>THIS IS NOT VALID CSS</style>
                </head>
            </html>
        """

        apple = document.Document(markup)
        apple.repair()

        self.assertEqual(0, len(apple._data.find_all('style')), 'All style tags should be removed.')

    def test_website_typo(self):
        """Confirm that the code corrects the typographical error in ismailinsight.org."""
        markup = """
            <html>
                <body>
                    <a href="https://www.ismailinsight.org">FIX THE TYPO</a>
                </body>
            </html>
        """

        apple = document.Document(markup)
        apple.repair()

        self.assertEqual("https://www.ismailiinsight.org", apple._data.a['href'],
                         'The typographical error in ismailinsight.org should be fixed.')

    def test_gray_background(self):
        """Confirm that the code adds in the gray background if it has been removed."""
        markup = """
            <html>
                <body>
                    <span>MOVE ME</span>
                </body>
            </html>
        """

        apple = document.Document(markup)
        apple.repair()

        self.assertIsNone(apple._data.body.find('span', recursive=False),
                          'The span tag should have been removed from the body tag.')
        div_tag = apple._data.body.find('div', recursive=False)
        self.assertTrue(div_tag is not None and div_tag['style'] == 'background-color: #595959;',
                        'The div tag should have been added to the body tag.')
        span_tag = apple._data.body.div.span
        self.assertTrue(span_tag is not None and span_tag.string == 'MOVE ME',
                        'The span tag should have been moved to the div tag.')
