from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.commands.results import FactorRef
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorNameError,
    EmptyNameError,
    FactorNotFoundError,
)
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class UpdateFactorCommand(Command[FactorRef]):
    table_id: int
    factor_id: int
    name: str | None = None
    order_index: int | None = None


class UpdateFactorHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: UpdateFactorCommand) -> FactorRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        if request.name is not None:
            if not request.name.strip():
                raise EmptyNameError("name")
            if any(f.name == request.name and f.id != factor.id for f in table.factors):
                raise DuplicateFactorNameError(request.name)
            factor.name = request.name
        if request.order_index is not None:
            factor.order_index = request.order_index

        await self._tables.save(table)
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)
