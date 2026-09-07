from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.domain.combination import parse_status
from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.combination_queries import (
    CombinationDTO,
    CombinationQueries,
)
from app.decision_tables.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
from app.decision_tables.ports.decision_table_queries import DecisionTableQueries
from app.decision_tables.queries._guards import validate_factor_value_pairs
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListCombinationsQuery(Query[Page[CombinationDTO]]):
    table_id: int
    status: str | None = None
    factor_values: tuple[tuple[int, int], ...] = ()
    page: PageRequest = field(default_factory=PageRequest)


class ListCombinationsHandler:
    def __init__(self, tables: DecisionTableQueries, combinations: CombinationQueries) -> None:
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: ListCombinationsQuery) -> Page[CombinationDTO]:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        validate_factor_value_pairs(table, list(request.factor_values))

        filter_ = CombinationFilter(
            status=parse_status(request.status) if request.status is not None else None,
            factor_values=tuple(
                FactorValueAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ),
        )
        return await self._combinations.list_(request.table_id, filter_, request.page)
