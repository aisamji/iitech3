"""A mock of the sqlite interface."""
import sqlite3
import re
from datetime import datetime
from unittest import mock

PARSE_DECLTYPES = 5

db_data = {
    'webpages':
        {'https://www.apple.com':
            ('https://www.apple.com', 200, datetime(2000, 1, 1, 12))
         },
    'emails':
        {'aisamji09@gmail.com':
            ('aisamji09@gmail.com', True, 'accepted_email', datetime(2000, 1, 1, 12))
         }
}
results = [None]


def _fetchone():
    global results
    a = results[0]
    del results[0]
    return a


def _execute(sql_statement, args=None):
    global results
    global db_data
    results = [None]
    match = re.match(r'SELECT \* FROM (.+) WHERE .+', sql_statement)
    if match is not None:
        table = match.group(1)
        try:
            results = [db_data[table][args[0]]]
        except KeyError:
            pass
    elif sql_statement == 'PRAGMA user_version':
        results = [(0,)]
    else:
        match = re.match(r'INSERT OR REPLACE INTO (.+) VALUES .+', sql_statement)
        if match is not None:
            table = match.group(1)
            db_data[table][args[0]] = args
    return cursor


cache_db = mock.MagicMock(sqlite3.Connection)
cache_db.executescript = mock.Mock(sqlite3.Connection.executescript)
cache_db.execute = mock.Mock(side_effect=_execute)
cursor = mock.MagicMock(sqlite3.Cursor)
cursor.fetchone = mock.Mock(side_effect=_fetchone)


def connect(db_path, **kwargs):
    """Get the cache_db."""
    return cache_db
