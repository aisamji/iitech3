"""A mock of the requests library."""
from unittest import mock
import json
import os
from requests import exceptions


class Response:
    """A mock of the Response object."""

    def close(self):
        """Do nothing."""
        pass

    def json(self):
        """Interpret the data as a json object."""
        return json.loads(self.text)

    def __init__(self, url, data_file=None, status_code=200):
        """Initialize the response object."""
        self.url = str(url)
        self.status_code = status_code
        if data_file is not None:
            with open(os.path.join('tests/files', data_file), 'rb') as file:
                self.content = file.read()
        else:
            self.content = b''
        self.text = str(self.content, 'UTF-8', errors='replace')
        print(self.url, self.content, self.text, sep='\n')

    def __str__(self):
        """Get the url of the response."""
        return self.url

    def __hash__(self):
        """Get a hash of the url for this object to allow it to be used as a key."""
        return hash(self.url)

    def __eq__(self, other):
        """Check whether this is equal to another object."""
        return self.url == str(other)

    def __ne__(self, other):
        """Check whether this is not equal to another object."""
        return not self.__eq__(other)


responses = {
    'https://www.google.com':
        Response('https://www.google.com'),
    'http://api.quickemailverification.com/v1/verify?email=richard@quickemailverification.com&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55':  # noqa
        Response('http://api.quickemailverification.com/v1/verify?email=richard@quickemailverification.com&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55',  # noqa
                 'richard_qem.email'),
    'http://api.quickemailverification.com/v1/verify?email=ali.samji@outlook.com&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55':  # noqa
        Response('http://api.quickemailverification.com/v1/verify?email=ali.samji@outlook.com&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55',  # noqa
                 'ali.samji.email'),
    'http://api.quickemailverification.com/v1/verify?email=lcc@usaji.org&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55':  # noqa
        Response('http://api.quickemailverification.com/v1/verify?email=lcc@usaji.org&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55',  # noqa
                 'lcc.email'),
    'https://www.shitface.org':
        Response('https://www.shitface.org', status_code=410),
    'https://journeyforhealth.org':
        Response('https://journeyforhealth.org'),
    'https://www.akfusa.org':
        Response('https://www.akfusa.org', status_code=403),
    'https://www.jubileeconcerts.ismaili':
        exceptions.ConnectionError(),
    'https://ismailiinsight.org/eNewsletterPro/uploadedimages/000001/National/07.14.2017/071417_National.jpg':
        Response('https://ismailiinsight.org/eNewsletterPro/uploadedimages/000001/National/07.14.2017/071417_National.jpg', # noqa
                 '071417_National.jpg')
    }


def _get(url):
    result = responses[url]
    if isinstance(result, Exception):
        raise result
    else:
        return result


get = mock.Mock(side_effect=_get)
