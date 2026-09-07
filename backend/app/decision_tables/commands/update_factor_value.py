from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.commands.results import FactorValueRef
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorValueError,
    EmptyNameError,
    FactorNotFoundError,
    FactorValueNotFoundError,
)
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class UpdateFactorValueCommand(Command[FactorValueRef]):
    table_id: int
    factor_id: int
    value_id: int
    value: str | None = None
    order_index: int | None = None


class UpdateFactorValueHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: UpdateFactorValueCommand) -> FactorValueRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        value = factor.get_value(request.value_id)
        if value is None:
            raise FactorValueNotFoundError(request.value_id)
        await ensure_not_generating(self._jobs, request.table_id)

        if request.value is not None:
            if not request.value.strip():
                raise EmptyNameError("value")
            if any(v.value == request.value and v.id != value.id for v in factor.values):
                raise DuplicateFactorValueError(request.value)
            value.value = request.value
        if request.order_index is not None:
            value.order_index = request.order_index

        await self._tables.save(table)
        return FactorValueRef(id=value.id, value=value.value, order_index=value.order_index)
