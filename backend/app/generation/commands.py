"""Write-side use cases for the `generation` module."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.combinations.entities import (
    Combination,
    CombinationValue,
    build_signature,
    decompose_index,
    total_combinations,
)
from app.combinations.ports.combination_repository import CombinationRepository
from app.generation.entities import (
    TERMINAL_STATUSES,
    GenerationJob,
    GenerationJobStatus,
)
from app.generation.errors import (
    CombinationCapExceededError,
    FactorHasNoValuesError,
    GenerationAlreadyInProgressError,
    GenerationJobNotFoundError,
    NoFactorsError,
)
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.generation.service import GenerationJobRef, to_ref
from app.shared.mediator.requests import Command
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_repository import DecisionTableRepository


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


@dataclass(frozen=True)
class CancelGenerationJobCommand(Command[GenerationJobRef]):
    job_id: int


class CancelGenerationJobHandler:
    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, request: CancelGenerationJobCommand) -> GenerationJobRef:
        job = await self._jobs.get(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)
        job.cancel()  # raises InvalidGenerationJobTransitionError if already terminal
        await self._jobs.save(job)
        return to_ref(job)


@dataclass(frozen=True)
class MarkGenerationJobFailedCommand(Command[GenerationJobRef]):
    job_id: int
    error_message: str


class MarkGenerationJobFailedHandler:
    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, request: MarkGenerationJobFailedCommand) -> GenerationJobRef:
        job = await self._jobs.get(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)
        job.fail(request.error_message)
        await self._jobs.save(job)
        return to_ref(job)


@dataclass(frozen=True)
class MarkStaleGenerationJobsFailedCommand(Command[int]):
    job_ids: list[int] = field(default_factory=list)
    error_message: str = "Interrupted by server restart"


class MarkStaleGenerationJobsFailedHandler:
    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, request: MarkStaleGenerationJobsFailedCommand) -> int:
        return await self._jobs.mark_failed_bulk(request.job_ids, request.error_message)


@dataclass(frozen=True)
class GenerateCombinationsBatchCommand(Command[GenerationJobRef]):
    """The batching command at the heart of the generation design (see the
    plan's "The mediator/async-job design" section and spec 002). One
    dispatch of this command = one unit of work = one transaction = one
    commit. The background loop (`generation/worker.py`) calls this
    repeatedly; it is itself a boundary, not a handler, so it may call the
    mediator in a loop without violating ADR 007's "handlers must not call
    the mediator" guardrail."""

    job_id: int
    batch_size: int = 500


class GenerateCombinationsBatchHandler:
    def __init__(
        self,
        jobs: GenerationJobRepository,
        tables: DecisionTableRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._jobs = jobs
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: GenerateCombinationsBatchCommand) -> GenerationJobRef:
        # Read live status/cursor fresh, inside this dispatch's own
        # transaction — the job row is the sole source of truth, so this
        # handler (and the loop driving it) carries no state of its own
        # and can safely resume after a crash or observe a concurrent
        # cancel (see spec 002).
        job = await self._jobs.get_for_update(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)

        if job.status in TERMINAL_STATUSES:
            # Idempotent no-op: already completed/failed/cancelled.
            return to_ref(job)

        job.start()

        table = await self._tables.get(job.decision_table_id)
        if table is None:
            raise DecisionTableNotFoundError(job.decision_table_id)

        ordered_factors = table.ordered_factors()
        value_counts = [len(f.values) for f in ordered_factors]

        batch_end = min(job.cursor + request.batch_size, job.total_combinations)
        new_combinations = [
            self._build_combination(job.decision_table_id, job.id or 0, ordered_factors, value_counts, index)
            for index in range(job.cursor, batch_end)
        ]

        await self._combinations.bulk_insert(new_combinations)
        job.record_batch(new_cursor=batch_end, rows_created=len(new_combinations))
        await self._jobs.save(job)

        return to_ref(job)

    @staticmethod
    def _build_combination(table_id: int, job_id: int, ordered_factors, value_counts, index: int) -> Combination:
        picks = decompose_index(index, value_counts)
        factor_value_ids = [
            ordered_factors[i].values[picks[i]].id or 0 for i in range(len(ordered_factors))
        ]
        return Combination(
            id=None,
            decision_table_id=table_id,
            generation_job_id=job_id,
            signature=build_signature(factor_value_ids),
            values=[
                CombinationValue(factor_id=ordered_factors[i].id or 0, factor_value_id=factor_value_ids[i])
                for i in range(len(ordered_factors))
            ],
        )
