"""The `DecisionTable` aggregate: a table, its ordered factors, and each
factor's ordered values. Small (dozens of rows) — loaded whole, mutated in
memory, saved whole via `DecisionTableRepository`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.shared.errors import EmptyNameError
from app.tables.errors import (
    DuplicateFactorNameError,
    DuplicateFactorValueError,
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)


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
        """Append a new value to this factor and return it.

        Raises:
            EmptyNameError: if `value` is blank.
            DuplicateFactorValueError: if `value` already exists on this factor.
        """
        if not value.strip():
            raise EmptyNameError("value")
        if any(v.value == value for v in self.values):
            raise DuplicateFactorValueError(value)
        factor_value = FactorValue(id=None, value=value, order_index=len(self.values))
        self.values.append(factor_value)
        return factor_value

    def get_value(self, value_id: int) -> FactorValue | None:
        """Return this factor's value with id `value_id`, or None if it has none."""
        return next((v for v in self.values if v.id == value_id), None)


@dataclass
class DecisionTable:
    id: int | None
    name: str
    description: str | None
    factors: list[Factor] = field(default_factory=list)

    def add_factor(self, name: str) -> Factor:
        """Append a new factor to this table and return it.

        Raises:
            EmptyNameError: if `name` is blank.
            DuplicateFactorNameError: if `name` already exists on this table.
        """
        if not name.strip():
            raise EmptyNameError("name")
        if any(f.name == name for f in self.factors):
            raise DuplicateFactorNameError(name)
        factor = Factor(id=None, name=name, order_index=len(self.factors))
        self.factors.append(factor)
        return factor

    def get_factor(self, factor_id: int) -> Factor | None:
        """Return this table's factor with id `factor_id`, or None if it has none."""
        return next((f for f in self.factors if f.id == factor_id), None)

    def ordered_factors(self) -> list[Factor]:
        """Return this table's factors sorted by `order_index`."""
        return sorted(self.factors, key=lambda f: f.order_index)

    def validate_factor_value_pairs(self, pairs: list[tuple[int, int]]) -> None:
        """Raise if any (factor_id, factor_value_id) pair doesn't belong to
        this table — used to validate bulk-filter and evaluate-assignment
        inputs before they reach the database (specs 003/004)."""
        for factor_id, factor_value_id in pairs:
            factor = self.get_factor(factor_id)
            if factor is None:
                raise UnknownFactorInFilterError(factor_id, self.id or 0)
            if factor.get_value(factor_value_id) is None:
                raise UnknownFactorValueInFilterError(factor_value_id, factor_id)

    def total_combinations(self) -> int:
        """Return the cartesian-product size of this table's factor values,
        or 0 if it has no factors or any factor has no values."""
        if not self.factors:
            return 0
        total = 1
        for factor in self.factors:
            if not factor.values:
                return 0
            total *= len(factor.values)
        return total
