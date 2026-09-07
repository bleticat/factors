"""Replays every rule for a table against its current combinations, in
creation order, so a later rule's output wins on any row both it and an
earlier rule match (see spec 005). Invoked automatically by the generation
worker once a job reaches `completed`, and exposed for on-demand use. Bounded
by the table's rule count (not by combination count), so — unlike
generation — it fits in a single command/transaction without batching.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._rule_apply import apply_rule
from app.decision_tables.commands.results import ReapplyRulesResult
from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class ReapplyRulesCommand(Command[ReapplyRulesResult]):
    table_id: int


class ReapplyRulesHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ReapplyRulesCommand) -> ReapplyRulesResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        rules = await self._rules.list_for_table(request.table_id)
        results = [await apply_rule(self._combinations, self._rules, rule) for rule in rules]
        return ReapplyRulesResult(results=results)
