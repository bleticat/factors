from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.commands.results import FactorRef
from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class AddFactorCommand(Command[FactorRef]):
    table_id: int
    name: str


class AddFactorHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: AddFactorCommand) -> FactorRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        await ensure_not_generating(self._jobs, request.table_id)

        factor = table.add_factor(request.name)
        await self._tables.save(table)
        assert factor.id is not None
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)
