from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class DeleteDecisionTableCommand(Command[None]):
    table_id: int


class DeleteDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: DeleteDecisionTableCommand) -> None:
        await self._tables.delete(request.table_id)
