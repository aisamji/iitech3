"""Custom exceptions that can be thrown by this program."""
# flake8: noqa

class IITech3Exception(Exception):
    """The base class for exception thrown by this program."""
    pass


# Caching exceptions
class CacheMissException(IITech3Exception):
    """Raised by the Cache when a requested entry is not available."""

    def __init__(self, value):
        """Raise an exception when the value is not found in the cache."""
        super().__init__('{!r:} is not in the cache.'.format(value))
