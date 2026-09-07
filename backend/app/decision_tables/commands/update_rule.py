"""Edits an existing rule's output/title/assignment in place, without
changing its position (`order_index`) — see spec 008/009. Reordering is a
separate command (`ReorderRulesCommand`), done from the "Saved rules" list;
any assignment is allowed regardless of how general it is relative to other
rules (spec 009) — a rule shadowed by a later, more general one is the
user's call to notice and fix (surfaced via `ListRuleOverlapsQuery`/
`ListRulesQuery`'s `shadowed_count`), not something the backend blocks.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._rule_apply import apply_rule
from app.decision_tables.commands.results import RuleRef
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorInAssignmentError,
    EmptyNameError,
    RuleNotFoundError,
)
from app.decision_tables.domain.rule import RuleAssignment
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class UpdateRuleCommand(Command[RuleRef]):
    table_id: int
    rule_id: int
    output: str | None = None
    title: str | None = None
    title_set: bool = False
    factor_values: tuple[tuple[int, int], ...] | None = None
    factor_values_set: bool = False


class UpdateRuleHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: UpdateRuleCommand) -> RuleRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        rule = await self._rules.get(request.table_id, request.rule_id)
        if rule is None:
            raise RuleNotFoundError(request.rule_id)

        if request.output is not None:
            if not request.output.strip():
                raise EmptyNameError("output")
            rule.output = request.output
        if request.title_set:
            rule.title = request.title.strip() if request.title and request.title.strip() else None

        if request.factor_values_set:
            assert request.factor_values is not None
            seen: set[int] = set()
            for factor_id, _ in request.factor_values:
                if factor_id in seen:
                    raise DuplicateFactorInAssignmentError(factor_id)
                seen.add(factor_id)
            table.validate_factor_value_pairs(list(request.factor_values))
            rule.factor_values = [
                RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ]

        await self._rules.save(rule)

        if request.factor_values_set or request.output is not None:
            applied = await apply_rule(self._combinations, self._rules, rule)
            return RuleRef(id=applied.rule_id, matched_count=applied.matched_count, applied_at=applied.applied_at)
        return RuleRef(id=rule.id, matched_count=rule.matched_count, applied_at=rule.applied_at)
