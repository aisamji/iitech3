"""Tests for the document class."""
import unittest
from unittest import mock
import bs4
import remocks
import cache
import document


class ReviewTests(unittest.TestCase):
    """A test suite for the review function."""

    def setUp(self):
        """Prepare the environment."""
        request_patcher = mock.patch('document.cache.requests', remocks)
        cache_patcher = mock.patch('document.cache.get_default', return_value=cache.Cache(':memory:'))
        self.addCleanup(request_patcher.stop)
        self.addCleanup(cache_patcher.stop)

        request_patcher.start()
        self.mock_default = cache_patcher.start()

        markup = """
            <body>
                <!-- Untouchables -->
                <a class="good" href="https://www.google.com" target="_blank">GOOD HYPERLINK</a>

                <!-- Useless Hyperlinks -->
                <a class="useless" href="">BLANK LINK</a>
                <a class="useless" href="##TrackClick##">POINTLESS TRACKER</a>

                <!-- Bad Hyperlinks -->
                <a class="broken" href="https://www.shitface.org">BROKEN HYPERLINK</a>
                <a class="unchecked" href="https://www.akfusa.org">UNCHECKABLE HYPERLINK</a>

                <!-- Double-tracked Hyperlinks -->
                <a class="double-tracked"
                   href="http://www.ismailiinsight.org/enewsletterpro/t.aspx?url=https%3A%2F%2Fjourneyforhealth.org">
                    DOUBLE TRACKED HYPERLINK
                </a>

                <!-- Misguided Hyperlinks -->
                <a class="untargetted" href="https://www.google.com">UNTARGETTED HYPERLINK</a>
                <a class="mistargetted" href="https://www.google.com" target="_self">MISTARGETTED HYPERLINK</a>
            </body>
        """

        self.apple = document.Document(markup)
        self.good_hyperlink = self.apple._data.find('a', class_='good')
        self.apple.review()

    def test_useless_hyperlinks(self):
        """Confirm that all useless hyperlinks are removed."""
        for l in self.apple._data.find_all(class_='useless'):
            self.assertIsNone(l, 'Useless hyperlinks should be removed.')
        self.assertIsNotNone(self.good_hyperlink,
                             'Useful hyperlinks should not be removed.')

    def test_hyperlink_marking(self):
        """Confirm that hyperlinks are marked correctly."""
        self.assertIsNotNone(self.apple._data.find(class_='broken'),
                             'Broken hyperlinks should be marked *BROKEN <code>*.')
        self.assertIsNotNone(self.apple._data.find('a', class_='unchecked'),
                             "Hyperlinks that cannot be checked should be marked *UNCHECKED*")
        self.assertEqual('GOOD HYPERLINK', self.good_hyperlink.text,
                         'Hyperlinks that are valid should not be marked at all.')

    def test_hyperlink_decoding(self):
        """Confirm that a doubly-tracked hyperlink is decoded correctly."""
        self.assertIsNotNone(self.apple._data.find('a', href='https://journeyforhealth.org'),
                             'Doubly-tracked hyperlinks should have their trackers removed and be decoded.')
        self.assertEqual('https://www.google.com', self.good_hyperlink['href'],
                         'Singly-tracked hyperlinks should not be modified.')

    def test_hyperlink_target_correction(self):
        """Confirm that all hyperlinks are set to open in a new window."""
        links = [
            self.apple._data.find('a', text='UNTARGETTED HYPERLINK'),
            self.apple._data.find('a', text='MISTARGETTED HYPERLINK'),
            self.good_hyperlink
        ]
        self.assertTrue(links[0].has_attr('target'),
                        'The target attribute should be automatically added to hyperlinks that do not have it.')
        for l in links:
            self.assertEqual('_blank', l['target'],
                             'All links should be set to open in a new window.')

    def test_jump_link_marking(self):
        """Confirm that all jump links are marked if they refer to a non-exsiting jump point."""
        markup = """
            <body>
                <a name="northpole">WELCOME TO THE NORTHPOLE</a>
                <a href="#northpole">WHERE IS SANTA CLAUS</a>
                <a href="#waldo">WHERE IS WALDO</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        links = apple._data.find_all('a')
        self.assertEqual('WELCOME TO THE NORTHPOLE', links[0].text,
                         'Anchors (ie jump points) should not be modified, only counted.')
        self.assertEqual('WHERE IS SANTA CLAUS', links[1].text,
                         'Working jump links should not be modified.')
        self.assertEqual('*MISSING waldo*WHERE IS WALDO', links[2].text,
                         'Broken jump links should be marked.')

    def test_email_cleaning(self):
        """Confirm that emails are cleaned if necessary."""
        markup = """
            <body>
                <a href="mailto:%20ali.samji%20@outlook.com">CLEAN ME :)</a>
                <a href="mailto:ali.samji@outlook.com">HANASE</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        links = apple._data.find_all('a')
        self.assertEqual('mailto:ali.samji@outlook.com', links[0]['href'],
                         'Emails with %20 characters in them should be cleaned.')
        self.assertEqual('mailto:ali.samji@outlook.com', links[1]['href'],
                         'Emails that do not need to be cleaned should not be modified.')

    def test_email_marking(self):
        """Confirm that emails are marked correctly."""
        markup = """
            <body>
                <a href="mailto:lcc@usaji.org">CANT CHECK ME</a>
                <a href="mailto:richard@quickemailverification.com">FAKE EMAIL</a>
                <a href="mailto:ali.samji@outlook.com">ILL BE GOOD, I PROMISE</a>
            </body>
        """

        apple = document.Document(markup)
        apple.review()

        self.assertEqual('*UNCHECKED*CANT CHECK ME', apple._data.find('a', href='mailto:lcc@usaji.org').text,
                         "Emails that can't be checked should be marked as such.")
        self.assertEqual('*INVALID rejected_email*FAKE EMAIL',
                         apple._data.find('a', href='mailto:richard@quickemailverification.com').text,
                         'Emails that are invalid should be marked as such.')
        self.assertEqual('ILL BE GOOD, I PROMISE', apple._data.find('a', href='mailto:ali.samji@outlook.com').text,
                         'Emails that are valid should not be marked.')


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
