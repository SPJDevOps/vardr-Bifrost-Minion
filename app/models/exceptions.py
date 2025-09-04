"""
Custom exceptions for the download minion application.
"""


class UserInputError(Exception):
    """Raised when there's an error in user input that should cause message rejection."""
    pass


class DependencyNotFoundError(Exception):
    """Raised when a required dependency is not found."""
    pass


class InternalError(Exception):
    """Raised when there's an internal error that should cause message nack."""
    pass 