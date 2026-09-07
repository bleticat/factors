from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands.results import DecisionTableRef
from app.decision_tables.domain.errors import DecisionTableNotFoundError, EmptyNameError
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class UpdateDecisionTableCommand(Command[DecisionTableRef]):
    table_id: int
    name: str | None = None
    description: str | None = None
    description_set: bool = False


class UpdateDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: UpdateDecisionTableCommand) -> DecisionTableRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        if request.name is not None:
            if not request.name.strip():
                raise EmptyNameError("name")
            table.name = request.name
        if request.description_set:
            table.description = request.description

        await self._tables.save(table)
        return DecisionTableRef(id=table.id, name=table.name, description=table.description)
