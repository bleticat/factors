from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.decision_table_queries import (
    DecisionTableDTO,
    DecisionTableQueries,
)
from app.shared.mediator.requests import Query


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
