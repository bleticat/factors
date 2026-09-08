"""Read-side use cases for the `rules` module."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from app.combinations.ports.combination_queries import (
    CombinationOverlapDTO,
    CombinationQueries,
    RuleFilterInput,
)
from app.combinations.ports.combination_repository import FactorValueAssignment
from app.rules.ports.rule_queries import RuleDTO, RuleQueries
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_queries import DecisionTableQueries


@dataclass(frozen=True)
class ListRulesQuery(Query[Page[RuleDTO]]):
    table_id: int
    page: PageRequest = field(default_factory=PageRequest)


class ListRulesHandler:
    def __init__(
        self, tables: DecisionTableQueries, rules: RuleQueries, combinations: CombinationQueries
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ListRulesQuery) -> Page[RuleDTO]:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        page = await self._rules.list_for_table(request.table_id, request.page)
        if not page.items:
            return page

        # Shadowing (spec 009) depends on every rule's position/assignment,
        # not just this page's — a rule on this page can be shadowed by one
        # that lives on a different page.
        all_rules = await self._rules.list_all_for_table(request.table_id)  # order_index order
        rule_inputs = [
            RuleFilterInput(
                rule_id=r.id,
                output=r.output,
                title=r.title,
                factor_values=tuple(
                    FactorValueAssignment(factor_id=fv.factor_id, factor_value_id=fv.factor_value_id)
                    for fv in r.factor_values
                ),
            )
            for r in all_rules
        ]
        shadowed_counts = await self._combinations.count_shadowed_matches(request.table_id, rule_inputs)
        if not shadowed_counts:
            return page

        items = [
            dataclasses.replace(rule, shadowed_count=shadowed_counts.get(rule.id, 0))
            for rule in page.items
        ]
        return Page(items=items, total=page.total, limit=page.limit, offset=page.offset)


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
