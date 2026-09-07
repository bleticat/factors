from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.commands.results import FactorValueRef
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    FactorNotFoundError,
)
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class AddFactorValueCommand(Command[FactorValueRef]):
    table_id: int
    factor_id: int
    value: str


class AddFactorValueHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: AddFactorValueCommand) -> FactorValueRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        value = factor.add_value(request.value)
        await self._tables.save(table)
        assert value.id is not None
        return FactorValueRef(id=value.id, value=value.value, order_index=value.order_index)
