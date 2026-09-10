from __future__ import annotations

from app.shared.errors import ValidationError


class InvalidRuleOrderError(ValidationError):
    """Spec 008: `ReorderRulesCommand` requires the full set of the table's
    rule ids, each exactly once — a reorder is a permutation, not a partial
    move."""

    def __init__(self, table_id: int) -> None:
        super().__init__(
            f"The given rule order must contain every rule of decision table {table_id} exactly once"
        )
        self.table_id = table_id
