from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.commands._rule_apply import apply_rule
from app.decision_tables.commands.results import RuleRef
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorInAssignmentError,
    EmptyNameError,
)
from app.decision_tables.domain.rule import Rule, RuleAssignment
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class CreateRuleCommand(Command[RuleRef]):
    table_id: int
    factor_values: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    output: str = ""


class CreateRuleHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: CreateRuleCommand) -> RuleRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        if not request.output.strip():
            raise EmptyNameError("output")

        seen: set[int] = set()
        for factor_id, _ in request.factor_values:
            if factor_id in seen:
                raise DuplicateFactorInAssignmentError(factor_id)
            seen.add(factor_id)
        table.validate_factor_value_pairs(list(request.factor_values))

        rule = Rule(
            id=None,
            decision_table_id=request.table_id,
            output=request.output,
            factor_values=[
                RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ],
        )
        rule = await self._rules.add(rule)

        applied = await apply_rule(self._combinations, self._rules, rule)
        return RuleRef(id=applied.rule_id, matched_count=applied.matched_count, applied_at=applied.applied_at)
