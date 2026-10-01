"""Internal helper logic `combinations.queries` delegates to. Not part of
the module's public request/response surface."""

from app.shared.errors import ValidationError
from app.tables.ports.decision_table_queries import DecisionTableDTO


def validate_factor_value_pairs(
    table: DecisionTableDTO, pairs: list[tuple[int, int]]
) -> None:
    """Validates against the `DecisionTableDTO` read shape rather than the
    `DecisionTable` domain aggregate (that variant, `DecisionTable.
    validate_factor_value_pairs`, is used by command handlers, which do have
    write-side repository access).

    Raises:
        ValidationError: if a pair names a factor or value not on `table`.

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
    app.shared.errors.ValidationError: Factor 99 does not belong to decision table 1
    """
    factors_by_id = {f.id: f for f in table.factors}
    for factor_id, factor_value_id in pairs:
        factor = factors_by_id.get(factor_id)
        if factor is None:
            raise ValidationError(
                f"Factor {factor_id} does not belong to decision table {table.id}"
            )
        if not any(v.id == factor_value_id for v in factor.values):
            raise ValidationError(
                f"Factor value {factor_value_id} does not belong to factor {factor_id}"
            )
