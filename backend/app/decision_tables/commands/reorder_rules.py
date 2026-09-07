"""Persists a complete new rule order for a table and immediately replays
every rule in that order (spec 008) — a reorder is a permutation of the
table's existing rule ids. Any order is allowed (spec 009): a rule that ends
up shadowed by a later, more general one is the user's call to notice
(surfaced via `shadowed_count`/`ListRuleOverlapsQuery`) and fix by dragging
it further down, not something the backend rejects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.commands._rule_apply import apply_rule
from app.decision_tables.commands.results import ReapplyRulesResult
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    InvalidRuleOrderError,
)
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class ReorderRulesCommand(Command[ReapplyRulesResult]):
    table_id: int
    ordered_rule_ids: tuple[int, ...] = field(default_factory=tuple)


class ReorderRulesHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ReorderRulesCommand) -> ReapplyRulesResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        existing = await self._rules.list_for_table(request.table_id)
        requested_ids = list(request.ordered_rule_ids)
        if len(requested_ids) != len(set(requested_ids)) or set(requested_ids) != {r.id for r in existing}:
            raise InvalidRuleOrderError(request.table_id)

        by_id = {r.id: r for r in existing}
        for position, rid in enumerate(requested_ids):
            by_id[rid].order_index = position
            await self._rules.save(by_id[rid])

        results = [await apply_rule(self._combinations, self._rules, by_id[rid]) for rid in requested_ids]
        return ReapplyRulesResult(results=results)
