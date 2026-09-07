from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._guards import ensure_not_generating
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    FactorNotFoundError,
)
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class DeleteFactorCommand(Command[None]):
    table_id: int
    factor_id: int


class DeleteFactorHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        jobs: GenerationJobRepository,
        combinations: CombinationRepository,
        rules: RuleRepository,
    ) -> None:
        self._tables = tables
        self._jobs = jobs
        self._combinations = combinations
        self._rules = rules

    async def handle(self, request: DeleteFactorCommand) -> None:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        table.factors = [f for f in table.factors if f.id != factor.id]
        await self._tables.save(table)
        # Deleting a factor invalidates every existing combination's
        # signature (see spec 001) — cascade the whole set for this table.
        await self._combinations.delete_all_for_table(request.table_id)
        # A rule's assignment may reference the deleted factor; rather than
        # silently narrowing its meaning, invalidate every rule for this
        # table too (see spec 005).
        await self._rules.delete_all_for_table(request.table_id)
