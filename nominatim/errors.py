"""
Custom exception and error classes for Nominatim.
"""

class UsageError(Exception):
    """ An error raised because of bad user input. This error will usually
        not cause a stack trace to be printed unless debugging is enabled.
    """
