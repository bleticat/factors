from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.decision_table_queries import DecisionTableQueries
from app.decision_tables.ports.rule_queries import RuleDTO, RuleQueries
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListRulesQuery(Query[Page[RuleDTO]]):
    table_id: int
    page: PageRequest = field(default_factory=PageRequest)


class ListRulesHandler:
    def __init__(self, tables: DecisionTableQueries, rules: RuleQueries) -> None:
        self._tables = tables
        self._rules = rules

    async def handle(self, request: ListRulesQuery) -> Page[RuleDTO]:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        return await self._rules.list_for_table(request.table_id, request.page)
