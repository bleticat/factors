"""Shared filter/assignment-pair validation for query handlers. Queries only
ever construct read-side query port adapters (see `app/composition.py`), so
this validates against the `DecisionTableDTO` read shape rather than the
`DecisionTable` domain aggregate (that variant, `DecisionTable.
validate_factor_value_pairs`, is used by command handlers, which do have
write-side repository access)."""

from __future__ import annotations

from app.decision_tables.domain.errors import (
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)
from app.decision_tables.ports.decision_table_queries import DecisionTableDTO


def validate_factor_value_pairs(table: DecisionTableDTO, pairs: list[tuple[int, int]]) -> None:
    factors_by_id = {f.id: f for f in table.factors}
    for factor_id, factor_value_id in pairs:
        factor = factors_by_id.get(factor_id)
        if factor is None:
            raise UnknownFactorInFilterError(factor_id, table.id)
        if not any(v.id == factor_value_id for v in factor.values):
            raise UnknownFactorValueInFilterError(factor_value_id, factor_id)
