"""A mock of the requests library."""
from unittest import mock
import json


class Response:
    """A mock of the Response object."""

    def close(self):
        """Do nothing."""
        pass

    def json(self):
        """Interpret the data as a json object."""
        return json.loads(self.text)

    def __init__(self, url, text=''):
        """Initialize the response object."""
        self.url = str(url)
        self.status_code = 200
        self.text = str(text)

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
    Response('https://www.google.com'),
    Response('richard@quickemailverification.com',
             '''{
                   "result":"invalid",
                   "reason":"rejected_email",
                   "disposable":"false",
                   "accept_all":"false",
                   "role":"false",
                   "email":"richard@quickemailverification.com",
                   "user":"richard",
                   "domain":"quickemailverification.com",
                   "safe_to_send":"false",
                   "success":"true",
                   "message":null
                   }''')
    }


get = mock.Mock(side_effect=responses)
