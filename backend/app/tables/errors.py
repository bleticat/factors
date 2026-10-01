from app.shared.errors import ValidationError


class DuplicateFactorNameError(ValidationError):
    """Raised when a factor name is already used by another factor in the
    same table."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Factor name {name!r} is already used in this table")
        self.name = name


class DuplicateFactorValueError(ValidationError):
    """Raised when a value is already used by another value on the same
    factor."""

    def __init__(self, value: str) -> None:
        super().__init__(f"Value {value!r} is already used in this factor")
        self.value = value


class UnknownFactorInFilterError(ValidationError):
    """Raised when a filter/assignment input references a factor that
    doesn't belong to the given table."""

    def __init__(self, factor_id: int, table_id: int) -> None:
        super().__init__(
            f"Factor {factor_id} does not belong to decision table {table_id}"
        )
        self.factor_id = factor_id
        self.table_id = table_id


class UnknownFactorValueInFilterError(ValidationError):
    """Raised when a filter/assignment input references a factor value that
    doesn't belong to the given factor."""

    def __init__(self, factor_value_id: int, factor_id: int) -> None:
        super().__init__(
            f"Factor value {factor_value_id} does not belong to factor {factor_id}"
        )
        self.factor_value_id = factor_value_id
        self.factor_id = factor_id
