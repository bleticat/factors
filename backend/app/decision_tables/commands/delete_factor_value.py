from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    FactorNotFoundError,
    FactorValueNotFoundError,
)
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class DeleteFactorValueCommand(Command[None]):
    table_id: int
    factor_id: int
    value_id: int


class DeleteFactorValueHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        jobs: GenerationJobRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._jobs = jobs
        self._combinations = combinations

    async def handle(self, request: DeleteFactorValueCommand) -> None:
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

        factor.values = [v for v in factor.values if v.id != value.id]
        await self._tables.save(table)
        # Same rationale as delete_factor.py: invalidates every existing
        # combination's signature for this table.
        await self._combinations.delete_all_for_table(request.table_id)
