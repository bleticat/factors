from __future__ import annotations

from app.shared.errors import ValidationError


class GenerationInProgressError(ValidationError):
    """Raised when a table's factors/values are mutated while a generation
    job is in flight for that table."""

    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"Decision table {table_id} has a generation job in progress; "
            "structure cannot change until it finishes"
        )
        self.table_id = table_id


class GenerationAlreadyInProgressError(ValidationError):
    """Raised when generation is requested for a table that already has an
    active generation job."""

    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"Decision table {table_id} already has a generation job in progress"
        )
        self.table_id = table_id


class InvalidGenerationJobTransitionError(ValidationError):
    """Raised when a generation job is asked to move to a status its current
    status doesn't allow (e.g. cancelling an already-terminal job)."""

    def __init__(self, job_id: int, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Generation job {job_id} cannot go from {from_status} to {to_status}"
        )
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status


class NoFactorsError(ValidationError):
    """Raised when generation is requested for a table that has no factors."""

    def __init__(self, table_id: int) -> None:
        super().__init__(f"Decision table {table_id} has no factors")
        self.table_id = table_id


class FactorHasNoValuesError(ValidationError):
    """Raised when generation is requested for a table with a factor that
    has no values."""

    def __init__(self, factor_id: int) -> None:
        super().__init__(f"Factor {factor_id} has no values")
        self.factor_id = factor_id


class CombinationCapExceededError(ValidationError):
    """Raised when a table's projected combination count exceeds the
    configured maximum."""

    def __init__(self, total: int, cap: int) -> None:
        super().__init__(
            f"Projected combination count {total} exceeds the maximum of {cap}"
        )
        self.total = total
        self.cap = cap
