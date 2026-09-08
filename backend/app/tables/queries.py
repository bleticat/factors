"""Read-side use cases for the `tables` module."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_queries import (
    DecisionTableDTO,
    DecisionTableQueries,
    DecisionTableSummaryDTO,
    FactorDTO,
)


@dataclass(frozen=True)
class GetDecisionTableQuery(Query[DecisionTableDTO]):
    table_id: int


class GetDecisionTableHandler:
    def __init__(self, queries: DecisionTableQueries) -> None:
        self._queries = queries

    async def handle(self, request: GetDecisionTableQuery) -> DecisionTableDTO:
        table = await self._queries.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        return table


@dataclass(frozen=True)
class ListDecisionTablesQuery(Query[Page[DecisionTableSummaryDTO]]):
    page: PageRequest = field(default_factory=PageRequest)


class ListDecisionTablesHandler:
    def __init__(self, queries: DecisionTableQueries) -> None:
        self._queries = queries

    async def handle(self, request: ListDecisionTablesQuery) -> Page[DecisionTableSummaryDTO]:
        return await self._queries.list_summaries(request.page)


@dataclass(frozen=True)
class ListFactorsQuery(Query[list[FactorDTO]]):
    table_id: int


class ListFactorsHandler:
    def __init__(self, queries: DecisionTableQueries) -> None:
        self._queries = queries

    async def handle(self, request: ListFactorsQuery) -> list[FactorDTO]:
        table = await self._queries.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        return table.factors
