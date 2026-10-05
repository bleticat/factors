from sqlalchemy import Select, exists
from sqlalchemy.sql import ColumnElement

from app.combinations.adapters.orm import CombinationRow, CombinationValueRow
from app.combinations.ports.combination_repository import CombinationFilter


def apply_combination_filter(
    stmt: Select, table_id: int, filter_: CombinationFilter
) -> Select:
    stmt = stmt.where(CombinationRow.decision_table_id == table_id)
    if filter_.status is not None:
        stmt = stmt.where(CombinationRow.status == str(filter_.status))
    for assignment in filter_.factor_values:
        stmt = stmt.where(
            _has_factor_value(assignment.factor_id, assignment.factor_value_id)
        )
    return stmt


def _has_factor_value(factor_id: int, factor_value_id: int) -> ColumnElement[bool]:
    return exists().where(
        CombinationValueRow.combination_id == CombinationRow.id,
        CombinationValueRow.factor_id == factor_id,
        CombinationValueRow.factor_value_id == factor_value_id,
    )
