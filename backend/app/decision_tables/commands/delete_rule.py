from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.domain.errors import RuleNotFoundError
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class DeleteRuleCommand(Command[None]):
    table_id: int
    rule_id: int


class DeleteRuleHandler:
    def __init__(self, rules: RuleRepository) -> None:
        self._rules = rules

    async def handle(self, request: DeleteRuleCommand) -> None:
        # Deleting a rule leaves whatever status/output it last set on
        # combinations untouched — see spec 005's "no revert on delete".
        deleted = await self._rules.delete(request.table_id, request.rule_id)
        if not deleted:
            raise RuleNotFoundError(request.rule_id)
