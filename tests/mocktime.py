"""A mock of the datetime module."""
import datetime as dt


class datetime:
    """A mock of the datetime object."""

    @classmethod
    def today(cls):
        """Get a datetime object representing July 4, 2017 11:06 AM."""
        return dt.datetime(2017, 7, 4, 11, 6)


timedelta = dt.timedelta
