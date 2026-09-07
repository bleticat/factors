from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.combination_queries import (
    CombinationOverlapDTO,
    CombinationQueries,
    RuleFilterInput,
)
from app.decision_tables.ports.combination_repository import FactorValueAssignment
from app.decision_tables.ports.decision_table_queries import DecisionTableQueries
from app.decision_tables.ports.rule_queries import RuleQueries
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class ListRuleOverlapsQuery(Query[Page[CombinationOverlapDTO]]):
    """See spec 006: rows matched by 2+ of the table's current rules,
    tagged with which rules matched and (last in id order) which one
    currently wins a reapply."""

    table_id: int
    page: PageRequest = field(default_factory=PageRequest)


class ListRuleOverlapsHandler:
    def __init__(
        self, tables: DecisionTableQueries, rules: RuleQueries, combinations: CombinationQueries
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ListRuleOverlapsQuery) -> Page[CombinationOverlapDTO]:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        rules = await self._rules.list_all_for_table(request.table_id)
        rule_inputs = [
            RuleFilterInput(
                rule_id=rule.id,
                output=rule.output,
                title=rule.title,
                factor_values=tuple(
                    FactorValueAssignment(factor_id=fv.factor_id, factor_value_id=fv.factor_value_id)
                    for fv in rule.factor_values
                ),
            )
            for rule in rules
        ]
        return await self._combinations.list_matched_by_multiple_rules(
            request.table_id, rule_inputs, request.page
        )
