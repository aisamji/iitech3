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
class UnknownTransform(IITech3Exception):
    """Raised by the Document during transformation when a content descriptor is invalid.."""

    def __init__(self, bad_descriptor, allowed_descriptors):
        """Create an exception listing the valid content descriptor."""
        super().__init__('{!s:} is not a valid content descriptor. '.format(bad_descriptor) +
                         'Please choose from {!s:}.'.format(allowed_descriptors))
