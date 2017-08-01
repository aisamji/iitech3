"""Classes and constants that represent an Ismaili Insight HTML newsletter."""
import re
import os
from collections import Counter
import bs4
import requests
from PIL import Image
import cache
import exceptions


# The review method should eventually . . .
# TODO: ensure all email addresses are hyperlinked.
# TODO: ensure all urls are hyperlinked.
# TODO: allow interactive edit when applicable.
class Document:
    """Represents an Ismaili Insight HTML newsletter."""

    # Class constants
    BASE_URL = 'https://ismailiinsight.org/eNewsletterPro/uploadedimages/000001/'

    def __init__(self, code):
        """Initialize a document from the given code."""
        code = str(code)
        if os.path.isfile(code):
            with open(code, 'r') as markup:
                data = markup.read()
            code = data
        # DOCTYPE fix for Ismaili Insight newsletter
        code = re.sub(
            r'<!DOCTYPE HTML PUBLIC “-//W3C//DTD HTML 4\.01 Transitional//EN” “http://www\.w3\.org/TR/html4/loose\.dtd”>', # noqa
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">',
            code, flags=re.I)
        self._data = bs4.BeautifulSoup(code, 'html5lib')

    # BeautifulSoup Search helpers
    @staticmethod
    def _is_anchor(tag):
        """Determine whether a tag creates a new anchor in the document."""
        return tag.name == 'a' and tag.get('name') is not None

    @staticmethod
    def _is_article_title(tag):
        """Determine whether the tag is an article title tag."""
        if tag.name != 'span' or tag.get('style') is None:
            return False
        count = 2
        count += 1 if 'background-color' in tag['style'] else 0
        count += 1 if 'font-family' in tag['style'] else 0
        return (
            re.search(r'^\s*$', tag.text) is None and
            'font-size: 16px' in tag['style'] and
            ('color: #595959' in tag['style'] or 'color: rgb(89, 89, 89)' in tag['style']) and
            tag['style'].count(';') == count
        )

    @staticmethod
    def _is_before_body(tag):
        """Determine whether the tag preceeds a non empty div tag."""
        next_div = tag.find_next_sibling('div')
        if tag.name != 'div' or next_div is None:
            return False
        return re.search(r'^\s*$', next_div.text) is None

    @staticmethod
    def _is_before_return(tag):
        """Determine whether the tag preceeds a Return to Top link."""
        next_tag = tag.find_next_sibling(lambda x: isinstance(x, bs4.Tag))
        if tag.name != 'div' or next_tag.name != 'a' or not next_tag.has_attr('href'):
            return False
        return next_tag['href'] == '#ReturnTop'

    # review method and helpers
    def _fix_external_link(self, link):
        """Fix an 'a' tag that references an external resource.

        Confirm that the 'a' tag is not useless.
        Confirm that the 'a' tag is set to open in a new window.
        Confirm that the 'a' tag does not have an existing tracking link.
        Confirm that the 'a' tag has a valid link.
        """
        result = {
            'removed': 0,
            'retargetted': 0,
            'decoded': 0,
            'broken': 0,
            'unchecked': 0
        }
        if link['href'] in ('##TrackClick##', '') or re.search(r'^\s*$', link.text) is not None:
            result['removed'] = 1
            link.decompose()
            return result

        if link.get('target') is None or link['target'].lower() != '_blank':
            result['retargetted'] = 1
            link['target'] = '_blank'

        match = re.match(r'http://www\.ismailiinsight\.org/enewsletterpro/(?:v|t)\.aspx\?.*url=(.+?)(?:&|$)',
                         link['href'], re.I)
        if match is not None:
            result['decoded'] = 1
            link['href'] = requests.compat.unquote_plus(match.group(1))

        if re.match(r'^##.+##$', link['href']) is None:
            url = re.sub(r'^##.+##', '', link['href'])  # strip off the ##TRACKCLICK## if applicable
            info = cache.get_default().get_webpage(url)

            if info.status == 403:
                result['unchecked'] = 1
                link.insert(0, '*UNCHECKED*')
            elif 400 <= info.status < 600:
                result['broken'] = 1
                link.insert(0, '*BROKEN {:d}*'.format(info.status))

        return result

    def _fix_internal_link(self, link, anchors):
        """Fix an 'a' tag that references an anchor in the document.

        Confirm that the 'a' tag is not useless.
        Confirm that the 'a' tag refers to an existing anchor.
        """
        result = {
            'removed': 0,
            'marked': 0
        }
        if re.search(r'^\s*$', link.text) is not None:
            result['removed'] = 1
            link.decompose()
            return result

        name = link['href'][1:]  # strip off the leading '#'
        if name not in anchors:
            result['marked'] = 1
            link.insert(0, '*MISSING {:s}*'.format(name))

        return result

    def _fix_email(self, email):
        """Fix an 'a' tag that composes an email.

        Confirm that the 'a' tag is not useless.
        Confirm that the 'a' tag has a valid email.
        Confirm that the 'a' tag does not have extra spaces (ie %20).
        """
        result = {
            'invalid': 0,
            'cleaned': 0,
            'unchecked': 0,
            'removed': 0
        }
        if re.search(r'^\s*$', email.text) is not None:
            result['removed'] = 1
            email.decompose()
            return result

        if re.search(r'%20', email['href']) is not None:
            result['cleaned'] = 1
            email['href'] = re.sub(r'%20', '', email['href'])

        address = email['href'][7:]  # strip off the leading mailto:
        info = cache.get_default().get_email(address)

        if not info.is_valid:
            if info.reason == 'accepted_email':
                result['unchecked'] = 1
                email.insert(0, '*UNCHECKED*')
            else:
                result['invalid'] = 1
                email.insert(0, '*INVALID {:s}*'.format(info.reason))
        return result

    def review(self):
        """Review the document for accuracy before sending it out.

        Ensure accuracy of all hyperlinks.
        Ensure accuracy of all anchors.
        Ensure accuracy of all mailto links.
        """
        result = {
            'links': Counter(),
            'anchors': Counter(),
            'emails': Counter()
        }

        external_links = self._data.find_all(
            'a',
            href=re.compile(r'^(?:##TrackClick##)?https?://(?:[a-z0-9]+\.)?[a-z0-9]+\.[a-z0-9]+|^##.+##$|^$', re.I)
        )
        for link in external_links:
            result['links'] += Counter(self._fix_external_link(link))

        anchors = [a['name'] for a in self._data.find_all(self._is_anchor)]
        internal_links = self._data.find_all(
            'a',
            href=re.compile(r'^#(?!#)')
        )
        for link in internal_links:
            result['anchors'] += Counter(self._fix_internal_link(link, anchors))

        emails = self._data.find_all(
            'a',
            href=re.compile(r'^mailto:', re.I)
        )
        for email in emails:
            result['emails'] += Counter(self._fix_email(email))

        return result

    # Repair method
    def repair(self):
        """Repair the document for any errors/bugs/typos/etc that are preventing it from loading correctly.

        Correct typo in ismailinsight.org.
        Remove all style tags.
        Ensure that the background of the document is gray.
        """
        result = {
            'typos': 0,
            'styles': 0,
            'background': 0
        }

        code = str(self._data)
        code, result['typos'] = re.subn(r'ismailinsight\.org', 'ismailiinsight.org', code, flags=re.I)
        self._data = bs4.BeautifulSoup(code, 'html5lib')

        for tag in self._data.find_all('style'):
            result['styles'] += 1
            tag.decompose()

        div_child = self._data.body.find('div', recursive=False)
        if div_child is None or div_child['style'] != 'background-color: #595959;':
            result['background'] = 1
            div = self._data.new_tag('div', style='background-color: #595959;')
            for i in range(len(self._data.body.contents)):
                div.append(self._data.body.contents[0].extract())
            self._data.body.append(div)

        return result

    # Transform method and helpers
    def _get_image_details(self, image_url):
        """Get the proper source, height and width of the image specified by the given partial url."""
        class RequestReader:
            def __init__(self, request_object):
                self._object = request_object

            def read(self):
                return self._object.content

        source = image_url if image_url.startswith('http') else (self.BASE_URL + image_url)
        data = Image.open(RequestReader(requests.get(source)))
        return {
            'source': source,
            'width': data.width,
            'height': data.height
        }

    def _add_hyperlink(self, parent_tag, descriptor):
        """Add an 'a' tag as specified by the descriptor."""
        if 'link' in descriptor:
            link_url = default_text = descriptor['link']
        elif 'file' in descriptor:
            link_url = self.BASE_URL + descriptor['file']
            default_text = descriptor['file'].rsplit('/')[-1]
        elif 'email' in descriptor:
            link_url = 'mailto:' + descriptor['email']
            default_text = descriptor['email']
        else:
            raise exceptions.UnknownTransform(descriptor, ['link', 'file', 'email'])

        a_tag = self._data.new_tag('a', href=link_url, target='_blank')
        try:
            self._set_content(a_tag, descriptor['text'])
        except KeyError:
            a_tag.string = default_text
        parent_tag.append(a_tag)

    def _set_content(self, parent_tag, content_list):
        """Convert the content_list to proper HTML and enclose with the given parent_tag."""
        if not isinstance(content_list, list):
            content_list = [content_list]
        parent_tag.clear()
        for item in content_list:
            if isinstance(item, dict):
                # Using a set intersection ((keys_to_search_for) & item.keys()),
                # The set will be empty when the keys are not found.
                # This takes advantage of the fact that empty == False and non-empty == True.
                if ('link', 'file', 'email') & item.keys():
                    self._add_hyperlink(parent_tag, item)
                else:
                    raise exceptions.UnknownTransform(item, ['link', 'file', 'email'])
            else:
                parent_tag.append(str(item))

    def _set_body(self, article_title, paragraph_list):
        """Overwrite the body of the given article with the new paragraphs."""
        before_tag = article_title.find_next_sibling(self._is_before_body)

        # Remove all existing paragraphs
        before_return = article_title.find_next_sibling(self._is_before_return)
        for tag in list(before_tag.next_siblings):
            if tag == before_return:
                break
            tag.extract()  # decompose does not exist for bs4.NavigableString

        # Add each paragraph in turn
        not_first_paragraph = False
        for descriptor in paragraph_list:
            if not_first_paragraph:
                before_tag.append(self._data.new_tag('br'))
            paragraph = self._data.new_tag('div',
                                           style='font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;') # noqa
            self._set_content(paragraph, descriptor)
            before_tag.insert_after(paragraph)
            not_first_paragraph = True
            before_tag = paragraph

    def apply(self, transforms):
        """Apply a transformation to the document (eg make all national changes to the document)."""
        if 'top' in transforms:
            front_image = self._data.find('img', src=re.compile('^https://www\.ismailiinsight\.org/enewsletterpro/public_templates/IsmailiInsight/images/20121101Top_1\.jpg$|National')) # noqa
            front_caption = front_image.parent.div

            image_data = self._get_image_details(transforms['top']['image'])
            front_image['src'] = image_data['source']
            front_image['width'] = image_data['width']
            front_image['height'] = image_data['height']
            self._set_content(front_caption, transforms['top']['caption'])
            del transforms['top']

        articles = self._data.find_all(self._is_article_title)
        for art in articles:
            title = art.text.strip()
            if title not in transforms:
                continue
            try:
                self._set_body(art, transforms[title]['body'])
            except KeyError:
                pass
            del transforms[title]

        return transforms

    # magic methods
    def __str__(self):
        """Get the html code of the document."""
        # DOCTYPE fix for Ismaili Insight newsletter
        code = re.sub(r'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4\.01 Transitional//EN" "http://www\.w3\.org/TR/html4/loose\.dtd">', # noqa
                      '<!DOCTYPE HTML PUBLIC “-//W3C//DTD HTML 4.01 Transitional//EN” “http://www.w3.org/TR/html4/loose.dtd”>', # noqa
                      str(self._data), flags=re.I)
        return code
