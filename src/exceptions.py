"""Custom exceptions that can be thrown by this program."""
# flake8: noqa

class IITech3Exception(Exception):
    """The base class for exception thrown by this program."""
    pass


# Caching exceptions
class CacheMissException(IITech3Exception):
    """Raised by the Cache when a requested entry is not available."""

    def __init__(self, value):
        """Create an exception stating that the value is not found in the cache."""
        super().__init__('{!r:} is not in the cache.'.format(value))

# Document Manipulation exceptions
class MissingTransformKey(IITech3Exception):
    """Raised by the Document during transformation when a valid transformation key is not found."""

    def __init__(self, bad_group, allowed_keys):
        """Create an exception listing the valid transform keys."""
        super().__init__('{!s:} does not contain a valid transform key. '.format(bad_group) +
                         'Please choose from {!s:}.'.format(allowed_keys))
