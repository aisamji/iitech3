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
        with open(os.path.join(current_dir, 'files/test.html'), 'r', encoding='UTF-8') as file:
            self._document = document.Document(file.read())
        with open(os.path.join(current_dir, 'files/transform.yml'), 'r', encoding='UTF-8') as file:
            with mock.patch('document.requests.get', remocks.get):
                self._remaining = self._document.apply(yaml.load(file))

    def test_top_transform(self):
        """Confirm that the new front image and caption is applied on the boilerplate picture."""
        desired_img = r'<img alt="##TrackClick##" class="top-image" height="267" src="https://ismailiinsight\.org/eNewsletterPro/uploadedimages/000001/National/07\.14\.2017/071417_National\.jpg" width="400"/>' # noqa
        desired_cap = r'<div class="top-caption" style="font-family: Segoe UI; font-size: 10px; color: #595959; text-align: justify;">\s*The caption can be a content descriptor or a list of content descriptors\.\s*</div>' # noqa

        tfrd_img = self._document._data.find('img', class_='top-image')
        tfrd_cap = self._document._data.find('div', class_='top-caption')

        self.assertIsNotNone(re.search(desired_img, str(tfrd_img)),
                             'The top image should be transformed to the new one.')
        self.assertIsNotNone(re.search(desired_cap, str(tfrd_cap)),
                             'The top caption should be transformed to the new one.')
        self.assertNotIn('top', self._remaining, 'The top transform should be marked as completed.')

    def test_article_transform(self):
        """Confirm that a paragraph list item can be a content descriptor or a list of content descriptors."""
        desired_first_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*This is a paragraph specified as a content descriptor\.\s*<br/>\s*</div>' # noqa
        desired_second_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">This is a paragraph specified\s*as a list of content descriptors\.\s*</div>' # noqa

        tfrd_first_para = self._document._data.find('div', class_='before-content-descriptor-para')
        tfrd_first_para = tfrd_first_para.find_next_sibling('div')
        tfrd_second_para = tfrd_first_para.find_next_sibling('div')

        self.assertIsNotNone(re.search(desired_first_para, str(tfrd_first_para)),
                             'The descriptor should be converted into a paragraph.')
        self.assertIsNotNone(re.search(desired_second_para, str(tfrd_second_para)),
                             'The The descriptors list should be converted into a paragraph.')
        self.assertNotIn('Content Descriptors Test', self._remaining,
                         'The content descriptors transform should be marked as completed.')

    def test_article_selection(self):
        """Confirm that only articles are selected."""
        all_articles = [
            'Content Descriptors Test',
            'Hyperlink Descriptors',
            'File Descriptor',
            'Email Descriptor',
            'Image Descriptor',
            'Bold Descriptor',
            'Italics Descriptor',
            'Underline Descriptor',
            'Anchor Descriptor',
            'Numbers Descriptor',
            'Bullets Descriptor'
        ]
        found_articles = list(map(lambda x: x.text.strip(),
                                  self._document._data.find_all(self._document._is_article_title)))

        self.assertEqual(all_articles, found_articles,
                         'Only proper articles should be selected.')

    def test_link_descriptor(self):
        """Confirm that link descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The link descriptor should be transformed into an "a" tag that opens in a new window\.\s*<a href="https://the\.ismaili/diamond-jubilee/gallery-diamond-jubilee-homage-ceremony" target="_blank">\s*An old link\.\s*</a>\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-link-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The link descriptor should be appended as an "a" tag to the content.')

    def test_file_descriptor(self):
        """Confirm that file descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The file descriptor should have the baseurl appended before being transformed\s*into an "a" tag that opens in a new window\.\s*<a href="https://ismailiinsight\.org/eNewsletterPro/uploadedimages/000001/NorthernTexas/AKSWB%20Hope\.pdf" target="_blank">\s*An old file\.\s*</a>\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-file-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The file descriptor should be appended as an "a" '
                             'tag with a link to the file on the eNP server.')

    def test_email_descriptor(self):
        """Confirm that the email descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The email descriptor should be transformed into a proper mailto link\.<a href="mailto:ali\.samji@outlook\.com" target="_blank">ali\.samji@outlook\.com</a>\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-email-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The email descriptor should be added as an "a" tag with a mailto link.')

    def test_image_descriptor(self):
        """Confirm that the image descriptors are properly generated."""
        desired_img_para = (r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*' # noqa
                            r'<table align="center" style="font-family: \'Segoe UI\';'
                            r' font-size: 13px; color: rgb\(89, 89, 89\);">\s*<tbody>\s*<tr>\s*'
                            r'<td style="text-align: center; vertical-align: middle;">\s*<img height="267"'
                            r' src="https://ismailiinsight\.org/eNewsletterPro/uploadedimages/000001/'
                            r'National/07\.14\.2017/071417_National\.jpg" width="400"/>\s*</td>\s*</tr>\s*<tr>\s*'
                            r'<td style="text-align: justify; vertical-align: middle; font-size: 10px;">\s*'
                            r'The image descriptor should be transformed into a proper img '
                            r'tag aligned via a table tag\.\s*</td>\s*</tr>\s*</tbody>\s*</table>\s*</div>')

        tfrd_img_para = self._document._data.find('div', class_='before-image-para')
        tfrd_img_para = tfrd_img_para.find_next_sibling('div')

        print(tfrd_img_para)
        self.assertIsNotNone(re.search(desired_img_para, str(tfrd_img_para)),
                             'The image descriptor should be converted to a 2-row table containing the image'
                             ' in the first row and the caption in the second.')

    def test_bold_descriptor(self):
        """Confirm that the bold descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The <strong>bold</strong> descriptor should enclose its text in a strong tag pair\.\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-bold-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The bold descriptor should be wrapped in a strong tag pair.')

    def test_italics_descriptor(self):
        """Confirm that the italics descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The <em>italics</em> descriptor should enclose its text in an em tag pair\.\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-italics-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The italics descriptor should be wrapped in an em tag pair.')

    def test_underline_descriptor(self):
        """Confirm that the underline descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The <u>underline</u> descriptor should enclose its text in a u tag pair\.\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-underline-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The underline descriptor should be wrapped in a u tag pair.')

    def test_anchor_descriptor(self):
        """Confirm that the anchor descriptors are properly generated."""
        desired_title = r'<span class="anchor-title" style="font-size: 16px; color: #595959; font-family: Segoe UI;">\s*<a name="bump">\s*Anchor Descriptor\s*</a>\s*</span>' # noqa
        tfrd_title = self._document._data.find('span', class_='anchor-title')

        print(tfrd_title)
        self.assertIsNotNone(re.search(desired_title, str(tfrd_title)),
                             'The title should be wrapped in an "a" with a name and transformed to the new title.')

    def test_jump_descriptor(self):
        """Confirm that the jump descriptors are properly generated."""
        desired_para = r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*The <a href="#bump">jump</a> descriptor should be transformed into an "a" tag the references an anchor\.\s*</div>' # noqa
        tfrd_para = self._document._data.find('div', class_='before-jump-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The jump descriptor should be transformed into an "a" tag'
                             ' that jumps to another part of the document.')

    def test_numbers_descriptor(self):
        """Confirm that the numbers descriptors are properly generated."""
        desired_para = (r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*<ol>\s*' # noqa
                        r'<li>\s*The numbers descriptor should be transformed into a numbered list\.\s*</li>\s*'
                        r'<li>\s*Each item can be a single content descriptor or a '
                        r'list of content descriptors\.\s*</li>\s*</ol>\s*</div>')
        tfrd_para = self._document._data.find('div', class_='before-numbers-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The numbers descriptor should be transformed into an ordered list.')

    def test_bullets_descriptor(self):
        """Confirm that the bullets descriptors are properly generated."""
        desired_para = (r'<div style="font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;">\s*<ul>\s*' # noqa
                        r'<li>\s*The bullets descriptor should be transformed into a bulleted list\.\s*</li>\s*'
                        r'<li>\s*Each item can be a single content descriptor or a '
                        r'list of content descriptors\.\s*</li>\s*</ul>\s*</div>')
        tfrd_para = self._document._data.find('div', class_='before-bullets-para')
        tfrd_para = tfrd_para.find_next_sibling('div')

        print(tfrd_para)
        self.assertIsNotNone(re.search(desired_para, str(tfrd_para)),
                             'The bullets descriptor should be transformed into an unordered list.')
