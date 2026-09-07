from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands.results import DecisionTableRef
from app.decision_tables.domain.decision_table import DecisionTable
from app.decision_tables.domain.errors import EmptyNameError
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class CreateDecisionTableCommand(Command[DecisionTableRef]):
    name: str
    description: str | None = None


class CreateDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: CreateDecisionTableCommand) -> DecisionTableRef:
        if not request.name.strip():
            raise EmptyNameError("name")
        table = await self._tables.add(
            DecisionTable(id=None, name=request.name, description=request.description)
        )
        assert table.id is not None
        return DecisionTableRef(id=table.id, name=table.name, description=table.description)
