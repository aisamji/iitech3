"""Classes and constants that represent an Ismaili Insight HTML newsletter."""
import re
import bs4
from requests import compat as urlfix
import cache


def debug(*args, **kwargs):
    """Print some text if in debug mode."""
    print(*args, **kwargs)


# The review method should eventually . . .
# TODO: ensure all internal links refer to a valid anchor.
# TODO: ensure all emails are valid.
# TODO: ensure all email addresses are hyperlinked.
# TODO: ensure all urls are hyperlinked.
# TODO: allow interactive edit when applicable.
class Document:
    """Represents an Ismaili Insight HTML newsletter."""

    def __init__(self, code):
        """Initialize a document from the given code."""
        code = code.replace('“', '"', 2).replace('”', '"', 2)  # DOCTYPE fix for Ismaili Insight newsletter
        self._data = bs4.BeautifulSoup(code, 'html5lib')

    @staticmethod
    def _is_external_link(link):
        """Determine whether link points to an external website."""
        if link.name != 'a' or link.get('href') is None:
            return False
        result = re.match(r'(?:##TrackClick##)?https?://(?:[a-z0-9]+\.)?[a-z0-9]+\.[a-z0-9]+|##.+##$',
                          link['href'], re.I)
        return result is not None

    def _fix_external_link(self, link):
        """Fix an 'a' tag that references an external resource.

        Confirm that the 'a' tag is set to open in a new window.
        """
        debug('\nExamining {!r:}'.format(link['href']))

        debug('Verifying usefulness . . . ', end='')
        if link['href'] in ('##TRACKCLICK##', ''):
            link.decompose()
            debug('REMOVED')
            return
        else:
            debug('NOT EMPTY')
            pass

        debug('Correcting target . . . ', end='')
        if link['target'] is None or link['target'].lower() != '_blank':
            link['target'] = '_blank'
            debug('SET TO NEW WINDOW')
        else:
            debug('NOTHING TO DO')
            pass

        debug('Cleaning extra tracker . . . ', end='')
        match = re.match(r'http://www\.ismailiinsight\.org/enewsletterpro/(?:v|t)\.aspx\?.*url=(.+?)(?:&|$)',
                         link['href'], re.I)
        if match is not None:
            link['href'] = urlfix.unquote_plus(match.group(1))
            debug('CLEANED')
        else:
            debug('NOTHING TO DO')
            pass

        debug('Validating url . . . ', end='')
        if re.match(r'^##.+##$', link['href']) is None:
            debug('Validating url . . . ', end='')
            url = re.sub(r'^##.+##', '', link['href'])
            info = cache.get_default().get_webpage(url)
            if 400 <= info.status < 600:
                debug('MARKED BROKEN')
                link.insert(0, '*BROKEN {:d}*'.format(info.status))
            else:
                debug('VALID')
                pass
        else:
            debug('VARIABLE NOT CHECKED')
            pass

    def review(self):
        """Review the document for errors.

        Ensure that all external links open in a new window.
        """
        external_links = self._data.find_all(self._is_external_link)
        [self._fix_external_link(link) for link in external_links]

    def __str__(self):
        """Get the html code of the document."""
        code = self._data.prettify().replace('"', '“', 1).replace('"', '”', 1)
        code = code.replace('"', '“', 1).replace('"', '”', 1)
        return code
