"""Internal helper logic `combinations.queries` delegates to. Not part of
the module's public request/response surface."""

from __future__ import annotations

from app.tables.errors import (
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)
from app.tables.ports.decision_table_queries import DecisionTableDTO


def validate_factor_value_pairs(
    table: DecisionTableDTO, pairs: list[tuple[int, int]]
) -> None:
    """Validates against the `DecisionTableDTO` read shape rather than the
    `DecisionTable` domain aggregate (that variant, `DecisionTable.
    validate_factor_value_pairs`, is used by command handlers, which do have
    write-side repository access).

    Raises:
        UnknownFactorInFilterError: if a pair names a factor not on `table`.
        UnknownFactorValueInFilterError: if a pair names a value not on that factor.

    >>> from app.tables.ports.decision_table_queries import FactorDTO, FactorValueDTO
    >>> table = DecisionTableDTO(
    ...     id=1, name="t", description=None,
    ...     factors=[FactorDTO(id=10, name="f", order_index=0,
    ...                         values=[FactorValueDTO(id=100, value="v", order_index=0)])],
    ... )
    >>> validate_factor_value_pairs(table, [(10, 100)])
    >>> validate_factor_value_pairs(table, [(99, 100)])
    Traceback (most recent call last):
        ...
    app.tables.errors.UnknownFactorInFilterError: Factor 99 does not belong to decision table 1
    """
    factors_by_id = {f.id: f for f in table.factors}
    for factor_id, factor_value_id in pairs:
        factor = factors_by_id.get(factor_id)
        if factor is None:
            raise UnknownFactorInFilterError(factor_id, table.id)
        if not any(v.id == factor_value_id for v in factor.values):
            raise UnknownFactorValueInFilterError(factor_value_id, factor_id)
