from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.ports.decision_table_queries import (
    DecisionTableQueries,
    DecisionTableSummaryDTO,
)
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListDecisionTablesQuery(Query[Page[DecisionTableSummaryDTO]]):
    page: PageRequest = field(default_factory=PageRequest)


class ListDecisionTablesHandler:
    def __init__(self, queries: DecisionTableQueries) -> None:
        self._queries = queries

    async def handle(self, request: ListDecisionTablesQuery) -> Page[DecisionTableSummaryDTO]:
        return await self._queries.list_summaries(request.page)
