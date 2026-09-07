from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._job_refs import to_ref
from app.decision_tables.commands.results import GenerationJobRef
from app.decision_tables.domain.combination import total_combinations
from app.decision_tables.domain.errors import (
    CombinationCapExceededError,
    DecisionTableNotFoundError,
    FactorHasNoValuesError,
    GenerationAlreadyInProgressError,
    NoFactorsError,
)
from app.decision_tables.domain.generation_job import GenerationJob, GenerationJobStatus
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class RequestGenerationCommand(Command[GenerationJobRef]):
    table_id: int


class RequestGenerationHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        jobs: GenerationJobRepository,
        combinations: CombinationRepository,
        max_combinations: int,
    ) -> None:
        self._tables = tables
        self._jobs = jobs
        self._combinations = combinations
        self._max_combinations = max_combinations

    async def handle(self, request: RequestGenerationCommand) -> GenerationJobRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        if not table.factors:
            raise NoFactorsError(request.table_id)
        for factor in table.factors:
            if not factor.values:
                raise FactorHasNoValuesError(factor.id or 0)
        if await self._jobs.has_active_job(request.table_id):
            raise GenerationAlreadyInProgressError(request.table_id)

        total = total_combinations([len(f.values) for f in table.factors])
        if total > self._max_combinations:
            raise CombinationCapExceededError(total, self._max_combinations)

        # Delete-and-recreate regeneration semantics (v1 scope, see spec 002).
        await self._combinations.delete_all_for_table(request.table_id)

        job = await self._jobs.add(
            GenerationJob(
                id=None,
                decision_table_id=request.table_id,
                status=GenerationJobStatus.PENDING,
                total_combinations=total,
            )
        )
        return to_ref(job)
