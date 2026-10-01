"""The only business-rule error types in the app. Every module raises one of
these directly, with a descriptive message, rather than deriving its own
domain-specific subclass — no production code branches on anything more
specific than these three kinds, so one type per kind is all the boundary
layer (API routers mapping NotFoundError -> 404, ValidationError -> 422,
InvariantViolationError -> 409) ever needs.

`ValidationError` vs. `InvariantViolationError`: a `ValidationError` is
wrong on its own terms — a blank field, an unparseable status, a filter
that assigns the same factor twice in one request — true regardless of
what's in the database. An `InvariantViolationError` is well-formed but
conflicts with existing persisted state or a state-machine rule — a
duplicate name, a mutation while generation is locked, a job transition
from a terminal status, a cap exceeded by the current data. The practical
test: would re-running the exact same request later, against different
data, succeed? If yes, it's an invariant violation, not a validation error.
"""


class AppError(Exception):
    """Base class for business-rule violations raised by command/query handlers."""


class NotFoundError(AppError):
    """Raised when a requested entity does not exist."""


class ValidationError(AppError):
    """Raised when a request is malformed or invalid on its own terms,
    independent of current persisted state."""


class InvariantViolationError(AppError):
    """Raised when a well-formed request conflicts with existing persisted
    state or a state-machine rule (e.g. a uniqueness constraint, a
    concurrency lock, an invalid status transition, a configured limit)."""
