from dataclasses import dataclass, field

from app.shared.errors import InvariantViolationError, ValidationError


@dataclass
class FactorValue:
    id: int | None
    value: str
    order_index: int


@dataclass
class Factor:
    id: int | None
    name: str
    order_index: int
    values: list[FactorValue] = field(default_factory=list)

    def add_value(self, value: str) -> FactorValue:
        if not value.strip():
            raise ValidationError("value must not be empty")
        if any(v.value == value for v in self.values):
            raise InvariantViolationError(
                f"Value {value!r} is already used in this factor"
            )
        factor_value = FactorValue(id=None, value=value, order_index=len(self.values))
        self.values.append(factor_value)
        return factor_value

    def get_value(self, value_id: int) -> FactorValue | None:
        return next((v for v in self.values if v.id == value_id), None)


@dataclass
class DecisionTable:
    id: int | None
    name: str
    description: str | None
    factors: list[Factor] = field(default_factory=list)

    def add_factor(self, name: str) -> Factor:
        if not name.strip():
            raise ValidationError("name must not be empty")
        if any(f.name == name for f in self.factors):
            raise InvariantViolationError(
                f"Factor name {name!r} is already used in this table"
            )
        factor = Factor(id=None, name=name, order_index=len(self.factors))
        self.factors.append(factor)
        return factor

    def get_factor(self, factor_id: int) -> Factor | None:
        return next((f for f in self.factors if f.id == factor_id), None)

    def ordered_factors(self) -> list[Factor]:
        return sorted(self.factors, key=lambda f: f.order_index)

    def validate_factor_value_pairs(self, pairs: list[tuple[int, int]]) -> None:
        for factor_id, factor_value_id in pairs:
            factor = self.get_factor(factor_id)
            if factor is None:
                raise ValidationError(
                    f"Factor {factor_id} does not belong to decision table {self.id or 0}"
                )
            if factor.get_value(factor_value_id) is None:
                raise ValidationError(
                    f"Factor value {factor_value_id} does not belong to factor {factor_id}"
                )

    def total_combinations(self) -> int:
        if not self.factors:
            return 0
        total = 1
        for factor in self.factors:
            if not factor.values:
                return 0
            total *= len(factor.values)
        return total
