from __future__ import annotations

from app.shared.errors import ValidationError


class GenerationInProgressError(ValidationError):
    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"Decision table {table_id} has a generation job in progress; "
            "structure cannot change until it finishes"
        )
        self.table_id = table_id


class GenerationAlreadyInProgressError(ValidationError):
    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"Decision table {table_id} already has a generation job in progress"
        )
        self.table_id = table_id


class InvalidGenerationJobTransitionError(ValidationError):
    def __init__(self, job_id: int, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Generation job {job_id} cannot go from {from_status} to {to_status}"
        )
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status


class NoFactorsError(ValidationError):
    def __init__(self, table_id: int) -> None:
        super().__init__(f"Decision table {table_id} has no factors")
        self.table_id = table_id


class FactorHasNoValuesError(ValidationError):
    def __init__(self, factor_id: int) -> None:
        super().__init__(f"Factor {factor_id} has no values")
        self.factor_id = factor_id


class CombinationCapExceededError(ValidationError):
    def __init__(self, total: int, cap: int) -> None:
        super().__init__(
            f"Projected combination count {total} exceeds the maximum of {cap}"
        )
        self.total = total
        self.cap = cap
