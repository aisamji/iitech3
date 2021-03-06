"""Classes and constants for managing the cache."""
import os
import sqlite3
import datetime
import requests
import exceptions


# Global variables to configure used by the class to allow for easy configuration
DB_PATH = '/Users/aisamji09/Projects/iitech3/data/cache.db'  # Set by setup.py according to the OS in use.
MAX_AGE = 14  # The age in days of a value before the cache considers it too old.

# TODO: Convert cache into Singletonish class that has a get_default method
# Private variables
_cache = None


# Custom adapters and converters to translate between python and sqlite data
def _convert_datetime(sql_value):
    return datetime.datetime.strptime(sql_value.decode('utf-8'), '%Y%m%d%H%M%S')


def _adapt_datetime(py_value):
    return py_value.strftime('%Y%m%d%H%M%S')


sqlite3.register_converter('DATETIME', _convert_datetime)
sqlite3.register_converter('BOOL', lambda x: bool(int(x)))
sqlite3.register_adapter(datetime.datetime, _adapt_datetime)
# Using sqlite3's builtin bool adapter


def get_default():
    """Get a cache object created with the default values."""
    global _cache
    if _cache is None:
        _cache = Cache(DB_PATH)
    return _cache


class InfoHolder:
    """A class that holds grouped information."""

    def __init__(self, **kwargs):
        """Convert the key word arguments into proper attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)


class Cache:
    """An object that provides methods to manage the information in the cache."""

    # Class constants
    WEBPAGE_GET_STATEMENT = 'SELECT * FROM webpages WHERE url=?'
    WEBPAGE_SET_STATEMENT = 'INSERT OR REPLACE INTO webpages VALUES (?, ?, ?)'
    EMAIL_GET_STATEMENT = 'SELECT * FROM emails WHERE address=?'
    EMAIL_SET_STATEMENT = 'INSERT OR REPLACE INTO emails VALUES (?, ?, ?, ?)'
    EMAIL_API_ENDPOINT = 'http://api.quickemailverification.com/v1/verify?email={:s}&apikey=e7c512323e3d0025bc7a94e59801abc1dc2f4a2d12ed295fef3b400b9e55' # noqa
    DB_MANAGEMENT_SCRIPTS = ["""
                             CREATE TABLE webpages (
                                url TEXT PRIMARY KEY NOT NULL,
                                status INTEGER NOT NULL,
                                last_lookup DATETIME NOT NULL
                             );

                             CREATE TABLE emails (
                                address TEXT PRIMARY KEY NOT NULL,
                                is_valid BOOL NOT NULL,
                                reason TEXT NOT NULL,
                                last_lookup DATETIME NOT NULL
                             );
                             """]
    DB_VERSION = len(DB_MANAGEMENT_SCRIPTS)

    # Methods
    def __init__(self, db_path):
        """Connect to a caching database.

        Create, upgrade, or open a caching databse at the specified path.
        """
        db_path = str(db_path)
        if db_path != ':memory:':
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._database = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        version = self._database.execute('PRAGMA user_version').fetchone()[0]
        if version < self.DB_VERSION:
            self._database.executescript(self.DB_MANAGEMENT_SCRIPTS[version])
        self._database.execute('PRAGMA user_version={:d}'.format(self.DB_VERSION))
        self._database.commit()

    def __del__(self):
        """Clean up the database connection used by the cache object."""
        self._database.close()

    # Methods for managing webpage information
    def lookup_webpage(self, url):
        """Lookup the status of the url online.

        Find the url online an get the status and store it in the cache.
        """
        url = str(url)
        try:
            response = requests.get(url)
            status_code = response.status_code
            response.close()
        except requests.exceptions.ConnectionError:
            status_code = 410
        self._database.execute(self.WEBPAGE_SET_STATEMENT,
                               (url, status_code, datetime.datetime.today()))
        self._database.commit()

    def get_webpage(self, url, *, nolookup=False):
        """Get the status of the given url.

        Check for the status of the url in the cache. Unless nolookup is true,
        use lookup_webpage to lookup the status online if it is not in the cache or
        if the data in the cache is too old.
        """
        url = str(url)
        nolookup = bool(nolookup)
        response = self._database.execute(self.WEBPAGE_GET_STATEMENT, (url,)).fetchone()
        try:
            if (datetime.datetime.today() - response[-1]) >= datetime.timedelta(days=MAX_AGE):
                if not nolookup:
                    self.lookup_webpage(url)
        except TypeError:
            if nolookup:
                raise exceptions.CacheMissException(url) from None
            else:
                self.lookup_webpage(url)
                response = self._database.execute(self.WEBPAGE_GET_STATEMENT, (url,)).fetchone()
        info = InfoHolder(url=response[0], status=response[1],
                          last_lookup=response[2])
        return info

    def set_webpage(self, url, status):
        """Manually set the status of the given url.

        Manually add or update the status of the url in the cache. The status must
        correspond to an HTTP status code. A full list of
        status codes is available at https://en.wikipedia.org/wiki/List_of_HTTP_status_codes.
        """
        url = str(url)
        status = int(status)
        self._database.execute(self.WEBPAGE_SET_STATEMENT,
                               (url, status, datetime.datetime.today()))
        self._database.commit()

    # Methods for managing email information
    def lookup_email(self, address):
        """Lookup the validity of the address online.

        Verify the validity of address by sending it a test email.
        """
        address = str(address)
        response = requests.get(self.EMAIL_API_ENDPOINT.format(address))
        results = response.json()
        self._database.execute(self.EMAIL_SET_STATEMENT,
                               (address, False if results['safe_to_send'] == 'false' else True,
                                results['reason'], datetime.datetime.today()))
        self._database.commit()
        response.close()

    def get_email(self, address, *, nolookup=False):
        """Get the validity of the address.

        Check for the validity of the address in the cache. Unless nolookup is true,
        use lookup_email to lookup the validity online if it is not in the cache or
        if the data in the cache is too old.
        """
        address = str(address)
        nolookup = bool(nolookup)
        response = self._database.execute(self.EMAIL_GET_STATEMENT, (address,)).fetchone()
        try:
            if (datetime.datetime.today() - response[-1]) >= datetime.timedelta(days=MAX_AGE):
                if not nolookup:
                    self.lookup_email(address)
        except TypeError:
            if nolookup:
                raise exceptions.CacheMissException(address) from None
            else:
                self.lookup_email(address)
                response = self._database.execute(self.EMAIL_GET_STATEMENT, (address,)).fetchone()
        info = InfoHolder(address=response[0], is_valid=response[1],
                          reason=response[2], last_lookup=response[3])
        return info

    def set_email(self, address, is_valid):
        """Manually set the validity of the address.

        Manually add or update the validity of the address in the cache. The
        is_valid must be a boolean value indicating the validity.
        """
        address = str(address)
        is_valid = bool(is_valid)
        reason = 'user_verified' if is_valid else 'user_refuted'
        self._database.execute(self.EMAIL_SET_STATEMENT,
                               (address, is_valid, reason,
                                datetime.datetime.today()))
        self._database.commit()
