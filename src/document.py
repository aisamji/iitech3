"""Classes and constants that represent an Ismaili Insight HTML newsletter."""
import re
import os
import bs4
from requests import compat as urlfix
import cache


# The review method should eventually . . .
# TODO: ensure all email addresses are hyperlinked.
# TODO: ensure all urls are hyperlinked.
# TODO: allow interactive edit when applicable.
class Document:
    """Represents an Ismaili Insight HTML newsletter."""

    def __init__(self, code):
        """Initialize a document from the given code."""
        code = str(code)
        if os.path.isfile(code):
            with open(code, 'r') as markup:
                data = markup.read()
            code = data
        # DOCTYPE fix for Ismaili Insight newsletter
        code = code.replace(
            '<!DOCTYPE HTML PUBLIC “-//W3C//DTD HTML 4.01 Transitional//EN” “http://www.w3.org/TR/html4/loose.dtd”>',
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">')
        self._data = bs4.BeautifulSoup(code, 'html5lib')

    # BeautifulSoup Search helpers
    @staticmethod
    def _is_external_link(tag):
        """Determine whether a tag is a link that points to an external resource."""
        if tag.name != 'a' or tag.get('href') is None:
            return False
        result = re.match(r'(?:##TrackClick##)?https?://(?:[a-z0-9]+\.)?[a-z0-9]+\.[a-z0-9]+|##.+##$|$',
                          tag['href'], re.I)
        return result is not None

    @staticmethod
    def _is_internal_link(tag):
        """Determine whether a tag is link that refers to an anchor in the document."""
        if tag.name != 'a' or tag.get('href') is None:
            return False
        result = re.match(r'#(?!#)', tag['href'])
        return result is not None

    @staticmethod
    def _is_anchor(tag):
        """Determine whether a tag creates a new anchor in the document."""
        return tag.name == 'a' and tag.get('name') is not None

    @staticmethod
    def _is_email(tag):
        """Determine whether a tag is a mailto link."""
        if tag.name != 'a' or tag.get('href') is None:
            return False
        result = re.match(r'mailto:', tag['href'], re.I)
        return result is not None

    # review method and helpers
    def _fix_external_link(self, link):
        """Fix an 'a' tag that references an external resource.

        Confirm that the 'a' tag does not have an empty link.
        Confirm that the 'a' tag is set to open in a new window.
        Confirm that the 'a' tag does not have an existing tracking link.
        Confirm that the 'a' tag has a valid link.
        """
        if link['href'] in ('##TRACKCLICK##', ''):
            link.decompose()
            return

        if link.get('target') is None or link['target'].lower() != '_blank':
            link['target'] = '_blank'

        match = re.match(r'http://www\.ismailiinsight\.org/enewsletterpro/(?:v|t)\.aspx\?.*url=(.+?)(?:&|$)',
                         link['href'], re.I)
        if match is not None:
            link['href'] = urlfix.unquote_plus(match.group(1))

        if re.match(r'^##.+##$', link['href']) is None:
            url = re.sub(r'^##.+##', '', link['href'])  # strip off the ##TRACKCLICK## if applicable
            info = cache.get_default().get_webpage(url)
            if info.status == 403:
                link.insert(0, '*UNCHECKED*')
            elif 400 <= info.status < 600:
                link.insert(0, '*BROKEN {:d}*'.format(info.status))

    def _fix_internal_link(self, link, anchors):
        """Fix an 'a' tag that references an anchor in the document.

        Confirm that the 'a' tag refers to an existing anchor.
        """
        name = link['href'][1:]  # strip off the leading '#'
        if name not in anchors:
            link.insert(0, '*NOTFOUND {:s}*'.format(name))

    def _fix_email(self, email):
        """Fix an 'a' tag that composes an email.

        Confirm that the 'a' tag has a valid email.
        """
        email['href'] = re.sub(r'%20', '', email['href'])  # remove unnecesary spaces
        address = email['href'][7:]  # strip off the leading mailto:

        info = cache.get_default().get_email(address)
        if not info.is_valid:
            if info.reason == 'accepted_email':
                email.insert(0, '*UNCHECKED*')
            else:
                email.insert(0, '*BAD {:s}*'.format(info.reason))

    def review(self):
        """Review the document for errors.

        Ensure that all external links open in a new window.
        """
        external_links = self._data.find_all(self._is_external_link)
        [self._fix_external_link(link) for link in external_links]
        anchors = [a['name'] for a in self._data.find_all(self._is_anchor)]
        internal_links = self._data.find_all(self._is_internal_link)
        [self._fix_internal_link(link, anchors) for link in internal_links]
        emails = self._data.find_all(self._is_email)
        [self._fix_email(email) for email in emails]

    # display method
    def __str__(self):
        """Get the html code of the document."""
        # DOCTYPE fix for Ismaili Insight newsletter
        code = self._data.prettify().replace(
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">',
            '<!DOCTYPE HTML PUBLIC “-//W3C//DTD HTML 4.01 Transitional//EN” “http://www.w3.org/TR/html4/loose.dtd”>')
        return code
