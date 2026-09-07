"""Cross-context error base classes.

Bounded contexts derive their own domain errors from these so boundary layers
(API routers) can map error *kinds* to protocol responses (e.g. NotFoundError
-> 404, ValidationError -> 422) without knowing every concrete error type.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for business-rule violations raised by command/query handlers."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class ValidationError(DomainError):
    """Raised when a request violates a business validation rule or invariant."""


class UnregisteredRequestError(Exception):
    """Raised by the mediator when no handler factory is registered for a request type."""

    def __init__(self, request_type: type) -> None:
        super().__init__(f"No handler registered for request type {request_type.__name__!r}")
        self.request_type = request_type
