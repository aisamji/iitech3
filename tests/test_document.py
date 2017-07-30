"""Tests for the document class."""
import unittest
from unittest import mock
import os
import re
import bs4
import yaml
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
                <a class="anchor" name="northpole">COUNTED ANCHOR</a>
                <a class="found" href="#northpole">GOOD JUMP</a>
                <a class="valid" href="mailto:ali.samji@outlook.com">GOOD EMAIL</a>

                <!-- Useless Hyperlinks -->
                <a class="useless" href="">BLANK LINK</a>
                <a class="useless" href="##TrackClick##">POINTLESS TRACKER</a>
                <a class="useless" href="https://www.google.com"></a>

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

                <!-- Bad Jump Links -->
                <a class="missing" href="#waldo">BAD JUMP</a>

                <!-- Useless Jump Links -->
                <a class="useless-jump" href="#pert1"></a>

                <!-- Bad Emails -->
                <a class="accept-all" href="mailto:lcc@usaji.org">UNCHECKABLE EMAIL</a>
                <a class="invalid" href="mailto:richard@quickemailverification.com">INVALID EMAIL</a>

                <!-- Dirty Emails -->
                <a class="dirty" href="mailto:%20ali.samji%20@outlook.com">DIRTY EMAIL</a>

                <!-- Useless Emails -->
                <a class="useless-email" href="mailto:ali.samji@outlook.com"></a>
            </body>
        """

        self.apple = document.Document(markup)
        self.good_hyperlink = self.apple._data.find('a', class_='good')
        self.good_anchor = self.apple._data.find('a', class_="anchor")
        self.good_jump = self.apple._data.find('a', class_="found")
        self.good_email = self.apple._data.find('a', class_="valid")
        self.apple.review()

    def test_useless_hyperlinks(self):
        """Confirm that all useless hyperlinks are removed."""
        self.assertEqual(0, len(self.apple._data.find_all(class_='useless')),
                         'Useless hyperlinks should be removed.')
        self.assertIsNotNone(self.good_hyperlink,
                             'Useful hyperlinks should not be removed.')

    def test_hyperlink_marking(self):
        """Confirm that hyperlinks are marked correctly."""
        self.assertEqual('*BROKEN 410*', self.apple._data.find(class_='broken').contents[0].string,
                         'Broken hyperlinks should be marked *BROKEN <code>*.')
        self.assertEqual('*UNCHECKED*', self.apple._data.find('a', class_='unchecked').contents[0].string,
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
            self.apple._data.find('a', class_='untargetted'),
            self.apple._data.find('a', class_='mistargetted'),
            self.good_hyperlink
        ]
        self.assertTrue(links[0].has_attr('target'),
                        'The target attribute should be automatically added to hyperlinks that do not have it.')
        for l in links:
            self.assertEqual('_blank', l['target'],
                             'All links should be set to open in a new window.')

    def test_useless_jump_link(self):
        """Confirm that useless jump links are removed."""
        self.assertIsNone(self.apple._data.find('a', class_='useless-jump'),
                          'Useless jump links should be removed.')
        self.assertIsNotNone(self.good_jump,
                             'Useful jump links should not be removed.')

    def test_jump_link_marking(self):
        """Confirm that all jump links are marked if they refer to a non-exsiting jump point."""
        self.assertEqual('COUNTED ANCHOR', self.good_anchor.text,
                         'Anchors (ie jump points) should not be modified, only counted.')
        self.assertEqual('GOOD JUMP', self.good_jump.text,
                         'Working jump links should not be modified.')
        self.assertEqual('*MISSING waldo*BAD JUMP', self.apple._data.find('a', class_='missing').text,
                         'Broken jump links should be marked.')

    def test_useless_emails(self):
        """Confirm that useless emails are removed."""
        self.assertIsNone(self.apple._data.find('a', class_='useless-email'),
                          'Useless emails should be removed.')
        self.assertIsNotNone(self.good_email,
                             'Useful emails should not be removed.')

    def test_email_cleaning(self):
        """Confirm that emails are cleaned if necessary."""
        self.assertEqual('mailto:ali.samji@outlook.com', self.apple._data.find('a', class_="dirty")['href'],
                         'Dirty emails should be cleaned.')
        self.assertEqual('mailto:ali.samji@outlook.com', self.good_email['href'],
                         'Emails that do not need to be should not be modified.')

    def test_email_marking(self):
        """Confirm that emails are marked correctly."""
        self.assertEqual('*UNCHECKED*', self.apple._data.find('a', class_="accept-all").contents[0].string,
                         "Emails that cannot be checked should be marked as such.")
        self.assertEqual('*INVALID rejected_email*',
                         self.apple._data.find('a', class_="invalid").contents[0].string,
                         'Emails that are invalid should be marked as such.')
        self.assertEqual('GOOD EMAIL', self.good_email.contents[0].string,
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


class TransformTests(unittest.TestCase):
    """A test suite for the apply method."""

    def setUp(self):
        """Prepare the environment before executing each test."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, 'files/original.html'), 'r', encoding='UTF-8') as file:
            self._work_doc = document.Document(file.read())
        with open(os.path.join(current_dir, 'files/transform.yml'), 'r') as file:
            with mock.patch('document.requests.get', remocks.get):
                self._remaining = self._work_doc.apply(yaml.load(file))
        with open(os.path.join(current_dir, 'files/done.html'), 'r', encoding='UTF-8') as file:
            self._done_doc = document.Document(file.read())

    def test_front(self):
        """Confirm that the new front image and caption is applied on the boilerplate picture."""
        working_image = self._work_doc._data.find('img', class_='front-image')
        final_image = self._done_doc._data.find('img', class_='front-image')

        # Get both captions and convert long runs of whitespace into a single space(chr 32).
        working_caption = self._work_doc._data.find('div', class_='front-caption')
        working_caption = re.sub(r'\s+', ' ', str(working_caption))
        final_caption = self._done_doc._data.find('div', class_='front-caption')
        final_caption = re.sub(r'\s+', ' ', str(final_caption))

        self.assertNotIn('front', self._remaining,
                         'The front transform should have been marked as applied.')
        self.assertEqual(str(final_image), str(working_image),
                         'The front image should have been transformed to the new one.')
        self.assertEqual(final_caption, working_caption,
                         'The front caption should have been transformed to the new one.')
