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
        if tag.get('style') is None:
            return False
        tag['style'] = tag['style'].lower()
        if tag.name != 'span':
            return False
        count = 1
        count += 1 if 'background-color' in tag['style'] else 0
        count += 1 if 'font-family' in tag['style'] else 0
        return (
            re.search(r'^\s*$', tag.text) is None and
            'font-size: 16px' in tag['style'] and
            ('color: #595959' in tag['style'] or 'color: rgb(89, 89, 89)' in tag['style']) and
            tag['style'].count(';') >= count
        )

    @staticmethod
    def _is_before_body(tag):
        """Determine whether the tag preceeds a non empty div tag."""
        next_div = tag.find_next_sibling('div')
        next_table = tag.find_next_sibling('table')
        if tag.name != 'div' or (next_div is None and next_table is None):
            return False
        return (re.search(r'^\s*$', next_div.text) is None or next_table is not None or
                next_div.find('img') is not None)

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
    @staticmethod
    def _ensure_quoted(url):
        """Ensure that the given url is quoted."""
        return requests.compat.quote(requests.compat.unquote(url))

    def _get_image_details(self, image_url):
        """Get the proper source, height and width of the image specified by the given partial url."""
        class RequestReader:
            def __init__(self, request_object):
                self._object = request_object

            def read(self):
                return self._object.content

        source = requests.compat.urljoin(self.BASE_URL, self._ensure_quoted(image_url))
        data = Image.open(RequestReader(requests.get(source)))
        return {
            'source': source,
            'width': data.width,
            'height': data.height
        }

    def _add_hyperlink(self, parent_tag, descriptor):
        """Add an 'a' tag as specified by the descriptor."""
        try:  # Try link descriptor
            default_text = descriptor['link']
            link_url = descriptor['link']
        except KeyError:
            try:  # Try file descriptor
                default_text = descriptor['file'].rsplit('/')[-1]
                link_url = requests.compat.urljoin(self.BASE_URL,
                                                   self._ensure_quoted(descriptor['file']))
            except KeyError:
                try:  # Try email descriptor
                    default_text = descriptor['email']
                    link_url = 'mailto:' + descriptor['email']
                except:
                    raise exceptions.UnknownTransform(descriptor, ['link', 'file', 'email'])

        # Create 'a' tag that opens in new window
        a_tag = self._data.new_tag('a', href=link_url, target='_blank')
        try:
            self._set_content(a_tag, descriptor['text'])
        except KeyError:
            a_tag.string = default_text
        parent_tag.append(a_tag)

    def _add_image(self, parent_tag, descriptor):
        """Add a 'table' tag that contains an image and, optionally, a caption."""
        # Add Image Row
        image_data = self._get_image_details(descriptor['image'])
        img_tag = self._data.new_tag('img', src=image_data['source'],
                                     width=image_data['width'],
                                     height=image_data['height'])
        td_img_tag = self._data.new_tag('td',
                                        style='text-align: center; vertical-align: middle;')
        td_img_tag.append(img_tag)
        tr_img_tag = self._data.new_tag('tr')
        tr_img_tag.append(td_img_tag)
        tbody_tag = self._data.new_tag('tbody')
        tbody_tag.append(tr_img_tag)

        # Add Caption Row, if applicable
        try:
            tr_cap_tag = self._data.new_tag('tr')
            td_cap_tag = self._data.new_tag('td',
                                            style='text-align: justify; vertical-align: middle; font-size: 10px;')
            self._set_content(td_cap_tag, descriptor['caption'])
            tr_cap_tag.append(td_cap_tag)
            tbody_tag.append(tr_cap_tag)
        except KeyError:
            pass
        table_tag = self._data.new_tag('table', align='center',
                                       style="font-family: 'Segoe UI'; font-size: 13px; color: rgb(89, 89, 89);")
        table_tag.append(tbody_tag)
        parent_tag.append(table_tag)

    def _add_formatted(self, parent_tag, descriptor):
        """Add an appropriate text formmating tag according to the descriptor."""
        try:  # Try bold descriptor
            content_list = descriptor['bold']
            format_tag = self._data.new_tag('strong')
        except KeyError:
            try:  # Try italics descriptor
                content_list = descriptor['italics']
                format_tag = self._data.new_tag('em')
            except KeyError:
                try:  # Try underline descriptor
                    content_list = descriptor['underline']
                    format_tag = self._data.new_tag('u')
                except KeyError:
                    raise exceptions.UnknownTransform(descriptor, ['bold', 'italics', 'underline'])

        self._set_content(format_tag, content_list)
        parent_tag.append(format_tag)

    def _add_navigation(self, parent_tag, descriptor):
        """Add an 'a' tag that drops an anchor or jumps to one."""
        a_tag = self._data.new_tag('a')
        try:  # Try anchor descriptor
            default_text = a_tag['name'] = descriptor['anchor']
        except KeyError:
            try:  # Try jump descriptor
                default_text = descriptor['jump']
                a_tag['href'] = '#' + descriptor['jump']
            except KeyError:
                raise exceptions.UnknownTransform(descriptor, ['anchor', 'jump'])

        try:
            self._set_content(a_tag, descriptor['text'])
        except KeyError:
            a_tag.string = default_text
        parent_tag.append(a_tag)

    def _add_list(self, parent_tag, descriptor):
        """Add an ol or a ul tag representing the list specified by the descriptor."""
        try:  # Try numbers descriptor
            list_items = descriptor['numbers']
            list_tag = self._data.new_tag('ol')
        except KeyError:
            try:  # Try bullets descriptor
                list_items = descriptor['bullets']
                list_tag = self._data.new_tag('ul')
            except KeyError:
                raise exceptions.UnknownTransform(descriptor, ['numbers', 'bullets'])

        for item in list_items:
            item_tag = self._data.new_tag('li')
            self._set_content(item_tag, item)
            list_tag.append(item_tag)
        parent_tag.append(list_tag)

    def _set_content(self, parent_tag, content_list):
        """Convert the content_list to proper HTML and enclose with the given parent_tag."""
        if not isinstance(content_list, list):
            content_list = [content_list]
        parent_tag.clear()
        for item in content_list:
            if isinstance(item, dict):
                hyperlinks = {'link', 'file', 'email'}
                formats = {'bold', 'italics', 'underline'}
                navigation = {'jump', 'anchor'}
                lists = {'numbers', 'bullets'}
                # Using set intersection ((keys_to_search_for) & item.keys()),
                # The set will be empty when the keys are not found.
                # This takes advantage of the fact that empty == False and non-empty == True.
                if hyperlinks & item.keys():
                    self._add_hyperlink(parent_tag, item)
                elif 'image' in item:
                    self._add_image(parent_tag, item)
                elif formats & item.keys():
                    self._add_formatted(parent_tag, item)
                elif navigation & item.keys():
                    self._add_navigation(parent_tag, item)
                elif lists & item.keys():
                    self._add_list(parent_tag, item)
                else:
                    raise exceptions.UnknownTransform(item,
                                                      hyperlinks + formats + navigation +
                                                      lists + {'image'})
            else:
                parent_tag.append(str(item))

    def _clear_body(self, before_body, after_body):
        """Clear the body of all pre-existing content."""
        for tag in list(before_body.next_siblings):
            if tag == after_body:
                break
            tag.extract()  # decompose does not exist for bs4.NavigableString

    def _get_br_tag(self):
        br_tag = self._data.new_tag('br')
        div_tag = self._data.new_tag('div',
                                      style='font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;') # noqa
        div_tag.append(br_tag)
        return div_tag

    def _add_paragraphs(self, reference_tag, transform_group, action):
        """Add the paragraphs after before_body or before after_body. Only one is required."""
        not_first_paragraph = False
        paragraph_list = transform_group[action]

        for descriptor in paragraph_list:
            paragraph_tag = self._data.new_tag('div',
                                               style='font-family: Segoe UI; font-size: 13px; color: #595959; text-align: justify;') # noqa
            self._set_content(paragraph_tag, descriptor)

            # Add a br tag between paragraphs
            # Add 2, if action is left or right
            if not_first_paragraph:
                reference_tag.append(self._get_br_tag())
                if action in ('left', 'right'):
                    reference_tag.append(self._get_br_tag())

            # Use the action to determine the relation between the paragraph and the reference
            if action in ('left', 'right') and not not_first_paragraph:
                reference_tag.append(paragraph_tag)
                reference_tag = paragraph_tag
            else:
                reference_tag.insert_after(paragraph_tag)
                reference_tag = paragraph_tag

            not_first_paragraph = True

    def _add_left_right(self, before_body, transform_group):
        """Add the content into a left column and a right column as specified by the transform group."""
        # Set content for each column
        left_td_tag = self._data.new_tag('td', style='vertical-align: middle;')
        self._add_paragraphs(left_td_tag, transform_group, 'left')
        right_td_tag = self._data.new_tag('td', style='vertical-align: middle;')
        self._add_paragraphs(right_td_tag, transform_group, 'right')

        # Create rest of the table and add it after the before_body tag
        tr_tag = self._data.new_tag('tr')
        tr_tag.append(left_td_tag)
        tr_tag.append(right_td_tag)

        tbody_tag = self._data.new_tag('tbody')
        tbody_tag.append(tr_tag)

        table_tag = self._data.new_tag('table',
                                       align='center',
                                       cellpadding='3',
                                       cellspacing='0')
        table_tag.append(tbody_tag)
        before_body.insert_after(table_tag)

    def apply(self, transforms):
        """Apply a transformation to the document (eg make all national changes to the document)."""
        if 'top' in transforms:
            front_image = self._data.find('img', src=re.compile(r'^https://www\.ismailiinsight\.org/enewsletterpro/public_templates/IsmailiInsight/images/20121101Top_1\.jpg$|National')) # noqa
            front_caption = front_image.parent.div

            image_data = self._get_image_details(transforms['top']['image'])
            front_image['src'] = image_data['source']
            front_image['width'] = image_data['width']
            front_image['height'] = image_data['height']
            self._set_content(front_caption, transforms['top']['caption'])
            del transforms['top']

        articles = self._data.find_all(self._is_article_title)
        for art in articles:
            if art.parent.name == 'a':
                art = art.parent
            title = art.text.strip()
            if title not in transforms:
                continue

            # Transform body
            # left/right specifiers override a body specifier
            before_body = art.find_next_sibling(self._is_before_body)
            after_body = art.find_next_sibling(self._is_before_return)

            if len({'body', 'left', 'right'} & transforms[title].keys()) != 0:
                self._clear_body(before_body, after_body)
                try:
                    self._add_left_right(before_body, transforms[title])
                    del transforms[title]['left']
                    del transforms[title]['right']
                except KeyError:
                    self._add_paragraphs(before_body, transforms[title], 'body')
                    del transforms[title]['body']

            # Transform title
            try:
                self._set_content(art, transforms[title]['title'])
                del transforms[title]['title']
            except KeyError:
                pass

            if len(transforms[title]) == 0:
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
