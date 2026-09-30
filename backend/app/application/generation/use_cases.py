"""Use cases for the `generation` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.generation.ports.queries import GenerationJobDTO
from app.application.ports.database import Database
from app.domain.combinations.entities import (
    Combination,
    CombinationValue,
    build_signature,
    decompose_index,
    total_combinations,
)
from app.domain.errors import NotFoundError
from app.domain.generation.entities import (
    TERMINAL_STATUSES,
    GenerationJob,
    GenerationJobStatus,
)
from app.domain.generation.errors import (
    CombinationCapExceededError,
    FactorHasNoValuesError,
    GenerationAlreadyInProgressError,
    NoFactorsError,
)


@dataclass(frozen=True)
class GenerationJobRef:
    id: int
    decision_table_id: int
    status: str
    total_combinations: int
    created_count: int
    error_message: str | None = None


def to_ref(job: GenerationJob) -> GenerationJobRef:
    assert job.id is not None
    return GenerationJobRef(
        id=job.id,
        decision_table_id=job.decision_table_id,
        status=str(job.status),
        total_combinations=job.total_combinations,
        created_count=job.created_count,
        error_message=job.error_message,
    )


class GenerationUseCases:
    """The `generation` module's use cases. Constructed once with the
    app's `Database`."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def request_generation(
        self, table_id: int, *, max_combinations: int
    ) -> GenerationJobRef:
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            if not table.factors:
                raise NoFactorsError(table_id)
            for factor in table.factors:
                if not factor.values:
                    raise FactorHasNoValuesError(factor.id or 0)
            if await uow.jobs.has_active_job(table_id):
                raise GenerationAlreadyInProgressError(table_id)

            total = total_combinations([len(f.values) for f in table.factors])
            if total > max_combinations:
                raise CombinationCapExceededError(total, max_combinations)

            # Delete-and-recreate regeneration semantics (v1 scope, see spec 002).
            await uow.combinations.delete_all_for_table(table_id)

            job = await uow.jobs.add(
                GenerationJob(
                    id=None,
                    decision_table_id=table_id,
                    status=GenerationJobStatus.PENDING,
                    total_combinations=total,
                )
            )
            return to_ref(job)

    async def cancel_generation_job(self, job_id: int) -> GenerationJobRef:
        async with self._database.unit_of_work() as uow:
            job = await uow.jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Generation job {job_id} not found")
            job.cancel()  # raises InvalidGenerationJobTransitionError if already terminal
            await uow.jobs.save(job)
            return to_ref(job)

    async def mark_generation_job_failed(
        self, job_id: int, error_message: str
    ) -> GenerationJobRef:
        async with self._database.unit_of_work() as uow:
            job = await uow.jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Generation job {job_id} not found")
            job.fail(error_message)
            await uow.jobs.save(job)
            return to_ref(job)

    async def mark_stale_generation_jobs_failed(
        self,
        job_ids: list[int] | None = None,
        error_message: str = "Interrupted by server restart",
    ) -> int:
        async with self._database.unit_of_work() as uow:
            return await uow.jobs.mark_failed_bulk(job_ids or [], error_message)

    async def generate_combinations_batch(
        self, job_id: int, batch_size: int = 500
    ) -> GenerationJobRef:
        """The batching use case at the heart of the generation design (see
        the plan's "The async-job design" section and spec 002).
        One call = one unit of work = one transaction = one commit. The
        background loop (`generation/worker.py`) calls this repeatedly; it
        is itself a boundary, not a use-case method, so it may loop over it
        freely.
        """
        async with self._database.unit_of_work() as uow:
            # Read live status/cursor fresh, inside this call's own
            # transaction — the job row is the sole source of truth, so
            # this method (and the loop driving it) carries no state of
            # its own and can safely resume after a crash or observe a
            # concurrent cancel (see spec 002).
            job = await uow.jobs.get_for_update(job_id)
            if job is None:
                raise NotFoundError(f"Generation job {job_id} not found")

            if job.status in TERMINAL_STATUSES:
                # Idempotent no-op: already completed/failed/cancelled.
                return to_ref(job)

            job.start()

            table = await uow.tables.get(job.decision_table_id)
            if table is None:
                raise NotFoundError(f"Decision table {job.decision_table_id} not found")

            ordered_factors = table.ordered_factors()
            value_counts = [len(f.values) for f in ordered_factors]

            batch_end = min(job.cursor + batch_size, job.total_combinations)
            new_combinations = [
                self._build_combination(
                    job.decision_table_id,
                    job.id or 0,
                    ordered_factors,
                    value_counts,
                    index,
                )
                for index in range(job.cursor, batch_end)
            ]

            await uow.combinations.bulk_insert(new_combinations)
            job.record_batch(new_cursor=batch_end, rows_created=len(new_combinations))
            await uow.jobs.save(job)

            return to_ref(job)

    @staticmethod
    def _build_combination(
        table_id: int, job_id: int, ordered_factors, value_counts, index: int
    ) -> Combination:
        picks = decompose_index(index, value_counts)
        factor_value_ids = [
            ordered_factors[i].values[picks[i]].id or 0
            for i in range(len(ordered_factors))
        ]
        return Combination(
            id=None,
            decision_table_id=table_id,
            generation_job_id=job_id,
            signature=build_signature(factor_value_ids),
            values=[
                CombinationValue(
                    factor_id=ordered_factors[i].id or 0,
                    factor_value_id=factor_value_ids[i],
                )
                for i in range(len(ordered_factors))
            ],
        )

    # --- Reads ------------------------------------------------------------------

    async def get_generation_job(self, job_id: int) -> GenerationJobDTO:
        job = await self._database.jobs_queries.get(job_id)
        if job is None:
            raise NotFoundError(f"Generation job {job_id} not found")
        return job

    async def list_stale_running_generation_jobs(self) -> list[int]:
        return await self._database.jobs_queries.list_stale_running()
