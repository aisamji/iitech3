"""Classes and constants that represent an Ismaili Insight HTML newsletter."""
import re
import os
from collections import Counter
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

    # review method and helpers
    def _fix_external_link(self, link):
        """Fix an 'a' tag that references an external resource.

        Confirm that the 'a' tag does not have an empty link.
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
        if link['href'] in ('##TrackClick##', ''):
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
            link['href'] = urlfix.unquote_plus(match.group(1))

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

        Confirm that the 'a' tag refers to an existing anchor.
        """
        result = {
            'marked': 0
        }
        name = link['href'][1:]  # strip off the leading '#'
        if name not in anchors:
            result['marked'] = 1
            link.insert(0, '*MISSING {:s}*'.format(name))

        return result

    def _fix_email(self, email):
        """Fix an 'a' tag that composes an email.

        Confirm that the 'a' tag has a valid email.
        """
        result = {
            'invalid': 0,
            'cleaned': 0,
            'unchecked': 0
        }
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
        """Review the document for errors.

        Ensure that all external links open in a new window.
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

    # display method
    def __str__(self):
        """Get the html code of the document."""
        # DOCTYPE fix for Ismaili Insight newsletter
        code = re.sub(r'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4\.01 Transitional//EN" "http://www\.w3\.org/TR/html4/loose\.dtd">', # noqa
                      '<!DOCTYPE HTML PUBLIC “-//W3C//DTD HTML 4.01 Transitional//EN” “http://www.w3.org/TR/html4/loose.dtd”>', # noqa
                      str(self._data), flags=re.I)
        return code
