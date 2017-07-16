"""Tests for the document class."""
import unittest
from unittest import mock
import re
import bs4
import remocks
import cache
import document


class DocumentTests(unittest.TestCase):
    """Test suite for the Document class."""

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


class ExternalLinkTests(unittest.TestCase):
    """A test suite to test the review function."""

    def setUp(self):
        """Prepare the environment."""
        request_patcher = mock.patch('document.cache.requests', remocks)
        cache_patcher = mock.patch('document.cache.get_default', return_value=cache.Cache(':memory:'))
        self.addCleanup(request_patcher.stop)
        self.addCleanup(cache_patcher.stop)

        request_patcher.start()
        self.mock_default = cache_patcher.start()

    def test_useless_links(self):
        """Confirm that only all useless links are removed."""
        markup = """
            <body>
                <a href="">BLANK LINK</a>
                <a href="##TrackClick##">POINTLESS TRACKER</a>
                <a href="https://www.google.com">USEFUL LINK</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        self.assertEqual(1, len(apple._data.find_all('a')), 'All useless links should be removed.')
        self.assertEqual('USEFUL LINK', apple._data.body.a.string, 'Useful links should not be touched.')

    def test_link_marking(self):
        """Confirm that links are marked correctly."""
        markup = """
            <body>
                <a href="https://www.shitface.org">GIVE ME 410</a>
                <a href="https://www.akfusa.org">CANT CHECK ME</a>
                <a href="https://www.google.com">UNTOUCHABLE</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        links = apple._data.find_all('a')
        self.assertEqual('*BROKEN 410*GIVE ME 410', links[0].text, 'Broken links should be marked *BROKEN <code>*.')
        self.assertEqual('*UNCHECKED*CANT CHECK ME', links[1].text,
                         "Links that cannot be checked should be marked *UNCHECKED*")
        self.assertEqual('UNTOUCHABLE', links[2].text, 'Links that are valid should not be marked at all.')

    def test_link_decoding(self):
        """Confirm that a doubly-tracked link is decoded correctly."""
        markup = """
            <body>
                <a href="http://www.ismailiinsight.org/enewsletterpro/t.aspx?url=https%3A%2F%2Fjourneyforhealth.org">
                    DECODE ME
                </a>
                <a href="https://journeyforhealth.org">LEAVE ME ALONE</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        links = apple._data.body.find_all('a')
        self.assertEqual('https://journeyforhealth.org', links[0]['href'],
                         'Doubly-tracked links should have their trackers removed and be decoded.')
        self.assertEqual('https://journeyforhealth.org', links[1]['href'],
                         'Singly-tracked links should be left alone.')

    def test_target_correction(self):
        """Confirm that all links are set to open in a new window."""
        markup = """
            <body>
                <a href="https://www.google.com">GIVE ME A TARGET</a>
                <a href="https://www.google.com" target="_self">DIRECT ME</a>
                <a href="https://www.google.com" target="_blank">IM THE GOOD ONE</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        links = apple._data.body.find_all('a')
        self.assertTrue(links[0].get('target') is not None and links[0]['target'] == '_blank',
                        'Links missing a target attribute should have it created and set to _blank.')
        self.assertTrue(links[1]['target'] == '_blank',
                        'Links with an incorrect target should have it changed to _blank.')
        self.assertTrue(links[2]['target'] == '_blank',
                        'Links that have a correct target attribute should not be changed.')


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
