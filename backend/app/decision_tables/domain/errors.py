from __future__ import annotations

from app.shared.errors import NotFoundError, ValidationError


class DecisionTableNotFoundError(NotFoundError):
    def __init__(self, table_id: int) -> None:
        super().__init__(f"Decision table {table_id} not found")
        self.table_id = table_id


class FactorNotFoundError(NotFoundError):
    def __init__(self, factor_id: int) -> None:
        super().__init__(f"Factor {factor_id} not found")
        self.factor_id = factor_id


class FactorValueNotFoundError(NotFoundError):
    def __init__(self, value_id: int) -> None:
        super().__init__(f"Factor value {value_id} not found")
        self.value_id = value_id


class GenerationJobNotFoundError(NotFoundError):
    def __init__(self, job_id: int) -> None:
        super().__init__(f"Generation job {job_id} not found")
        self.job_id = job_id


class CombinationNotFoundError(NotFoundError):
    def __init__(self, combination_id: int) -> None:
        super().__init__(f"Combination {combination_id} not found")
        self.combination_id = combination_id


class RuleNotFoundError(NotFoundError):
    def __init__(self, rule_id: int) -> None:
        super().__init__(f"Rule {rule_id} not found")
        self.rule_id = rule_id


class DuplicateFactorNameError(ValidationError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Factor name {name!r} is already used in this table")
        self.name = name


class DuplicateFactorValueError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(f"Value {value!r} is already used in this factor")
        self.value = value


class EmptyNameError(ValidationError):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must not be empty")
        self.field = field


class GenerationInProgressError(ValidationError):
    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"Decision table {table_id} has a generation job in progress; "
            "structure cannot change until it finishes"
        )
        self.table_id = table_id


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


class GenerationAlreadyInProgressError(ValidationError):
    def __init__(self, table_id: int) -> None:
        super().__init__(f"Decision table {table_id} already has a generation job in progress")
        self.table_id = table_id


class InvalidGenerationJobTransitionError(ValidationError):
    def __init__(self, job_id: int, from_status: str, to_status: str) -> None:
        super().__init__(f"Generation job {job_id} cannot go from {from_status} to {to_status}")
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status


class InvalidCombinationStatusError(ValidationError):
    def __init__(self, status: str) -> None:
        super().__init__(f"{status!r} is not a valid combination status")
        self.status = status


class UnknownFactorInFilterError(ValidationError):
    def __init__(self, factor_id: int, table_id: int) -> None:
        super().__init__(f"Factor {factor_id} does not belong to decision table {table_id}")
        self.factor_id = factor_id
        self.table_id = table_id


class UnknownFactorValueInFilterError(ValidationError):
    def __init__(self, factor_value_id: int, factor_id: int) -> None:
        super().__init__(f"Factor value {factor_value_id} does not belong to factor {factor_id}")
        self.factor_value_id = factor_value_id
        self.factor_id = factor_id


class DuplicateFactorInAssignmentError(ValidationError):
    def __init__(self, factor_id: int) -> None:
        super().__init__(f"Factor {factor_id} is assigned more than once in the same request")
        self.factor_id = factor_id
