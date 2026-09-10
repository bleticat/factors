from __future__ import annotations

from app.shared.errors import ValidationError


class DuplicateFactorNameError(ValidationError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Factor name {name!r} is already used in this table")
        self.name = name


class DuplicateFactorValueError(ValidationError):
    def __init__(self, value: str) -> None:
        super().__init__(f"Value {value!r} is already used in this factor")
        self.value = value


class UnknownFactorInFilterError(ValidationError):
    def __init__(self, factor_id: int, table_id: int) -> None:
        super().__init__(
            f"Factor {factor_id} does not belong to decision table {table_id}"
        )
        self.factor_id = factor_id
        self.table_id = table_id


class UnknownFactorValueInFilterError(ValidationError):
    def __init__(self, factor_value_id: int, factor_id: int) -> None:
        super().__init__(
            f"Factor value {factor_value_id} does not belong to factor {factor_id}"
        )
        self.factor_value_id = factor_value_id
        self.factor_id = factor_id
