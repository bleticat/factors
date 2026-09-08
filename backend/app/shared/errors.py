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


class EmptyNameError(ValidationError):
    """A required name/value/output field was blank. Raised by more than one
    module (`tables`, `rules`), so it lives here rather than in one of them."""

    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must not be empty")
        self.field = field


class DuplicateFactorInAssignmentError(ValidationError):
    """A factor-value assignment input (rule, evaluate) names the same
    factor twice. Raised by both `rules` and `combinations`, so it lives
    here rather than in one of them."""

    def __init__(self, factor_id: int) -> None:
        super().__init__(f"Factor {factor_id} is assigned more than once in the same request")
        self.factor_id = factor_id


class UnregisteredRequestError(Exception):
    """Raised by the mediator when no handler factory is registered for a request type."""

    def __init__(self, request_type: type) -> None:
        super().__init__(f"No handler registered for request type {request_type.__name__!r}")
        self.request_type = request_type
