"""Custom exceptions that can be thrown by this program."""
# flake8: noqa

class IITech3Exception(Exception):
    """The base class for exception thrown by this program."""
    pass


# Caching exceptions
class CacheMissException(IITech3Exception):
    """Raised by the Cache when a requested entry is not available."""
    pass
