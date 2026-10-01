"""Cross-context error base classes.

Bounded contexts derive their own domain errors from these so boundary layers
(API routers) can map error *kinds* to protocol responses (e.g. NotFoundError
-> 404, ValidationError -> 422) without knowing every concrete error type.
"""


class AppError(Exception):
    """Base class for business-rule violations raised by command/query handlers."""


class NotFoundError(AppError):
    """Raised when a requested entity does not exist."""


class ValidationError(AppError):
    """Raised when a request violates a business validation rule or invariant."""
