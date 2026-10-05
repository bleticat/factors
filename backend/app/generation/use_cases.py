from dataclasses import dataclass

from app.combinations.entities import (
    Combination,
    CombinationValue,
    build_signature,
    decompose_index,
    total_combinations,
)
from app.generation.entities import (
    TERMINAL_STATUSES,
    GenerationJob,
    GenerationJobStatus,
)
from app.shared.errors import InvariantViolationError, NotFoundError
from app.shared.ports.database import Database

# --- Requests/responses -------------------------------------------------


@dataclass(frozen=True)
class RequestGenerationRequest:
    table_id: int
    max_combinations: int


@dataclass(frozen=True)
class RequestGenerationResponse:
    job: GenerationJob


@dataclass(frozen=True)
class CancelGenerationJobRequest:
    job_id: int


@dataclass(frozen=True)
class CancelGenerationJobResponse:
    job: GenerationJob


@dataclass(frozen=True)
class MarkGenerationJobFailedRequest:
    job_id: int
    error_message: str


@dataclass(frozen=True)
class MarkGenerationJobFailedResponse:
    job: GenerationJob


@dataclass(frozen=True)
class MarkStaleGenerationJobsFailedRequest:
    job_ids: list[int] | None = None
    error_message: str = "Interrupted by server restart"


@dataclass(frozen=True)
class MarkStaleGenerationJobsFailedResponse:
    updated_count: int


@dataclass(frozen=True)
class GenerateCombinationsBatchRequest:
    job_id: int
    batch_size: int = 500


@dataclass(frozen=True)
class GenerateCombinationsBatchResponse:
    job: GenerationJob


@dataclass(frozen=True)
class GetGenerationJobRequest:
    job_id: int


@dataclass(frozen=True)
class GetGenerationJobResponse:
    job: GenerationJob


@dataclass(frozen=True)
class ListStaleRunningGenerationJobsResponse:
    job_ids: list[int]


class GenerationUseCases:
    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def request_generation(
        self, request: RequestGenerationRequest
    ) -> RequestGenerationResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            if not table.factors:
                raise InvariantViolationError(
                    f"Decision table {request.table_id} has no factors"
                )
            for factor in table.factors:
                if not factor.values:
                    raise InvariantViolationError(
                        f"Factor {factor.id or 0} has no values"
                    )
            if await db.jobs.has_active_job(request.table_id):
                raise InvariantViolationError(
                    f"Decision table {request.table_id} already has a "
                    "generation job in progress"
                )

            total = total_combinations([len(f.values) for f in table.factors])
            if total > request.max_combinations:
                raise InvariantViolationError(
                    f"Projected combination count {total} exceeds the maximum "
                    f"of {request.max_combinations}"
                )

            # Delete-and-recreate regeneration semantics (v1 scope, see spec 002).
            await db.combinations.delete_all_for_table(request.table_id)

            job = await db.jobs.add(
                GenerationJob(
                    id=None,
                    decision_table_id=request.table_id,
                    status=GenerationJobStatus.PENDING,
                    total_combinations=total,
                )
            )
            return RequestGenerationResponse(job=job)

    async def cancel_generation_job(
        self, request: CancelGenerationJobRequest
    ) -> CancelGenerationJobResponse:
        async with self._database.transaction() as db:
            job = await db.jobs.get(request.job_id)
            if job is None:
                raise NotFoundError(f"Generation job {request.job_id} not found")
            job.cancel()  # raises InvariantViolationError if already terminal
            await db.jobs.save(job)
            return CancelGenerationJobResponse(job=job)

    async def mark_generation_job_failed(
        self, request: MarkGenerationJobFailedRequest
    ) -> MarkGenerationJobFailedResponse:
        async with self._database.transaction() as db:
            job = await db.jobs.get(request.job_id)
            if job is None:
                raise NotFoundError(f"Generation job {request.job_id} not found")
            job.fail(request.error_message)
            await db.jobs.save(job)
            return MarkGenerationJobFailedResponse(job=job)

    async def mark_stale_generation_jobs_failed(
        self,
        request: MarkStaleGenerationJobsFailedRequest = (
            MarkStaleGenerationJobsFailedRequest()
        ),
    ) -> MarkStaleGenerationJobsFailedResponse:
        async with self._database.transaction() as db:
            updated = await db.jobs.mark_failed_bulk(
                request.job_ids or [], request.error_message
            )
            return MarkStaleGenerationJobsFailedResponse(updated_count=updated)

    async def generate_combinations_batch(
        self, request: GenerateCombinationsBatchRequest
    ) -> GenerateCombinationsBatchResponse:
        async with self._database.transaction() as db:
            # Read live status/cursor fresh, inside this call's own
            # transaction — the job row is the sole source of truth, so
            # this method (and the loop driving it) carries no state of
            # its own and can safely resume after a crash or observe a
            # concurrent cancel (see spec 002).
            job = await db.jobs.get_for_update(request.job_id)
            if job is None:
                raise NotFoundError(f"Generation job {request.job_id} not found")

            if job.status in TERMINAL_STATUSES:
                # Idempotent no-op: already completed/failed/cancelled.
                return GenerateCombinationsBatchResponse(job=job)

            job.start()

            table = await db.tables.get(job.decision_table_id)
            if table is None:
                raise NotFoundError(f"Decision table {job.decision_table_id} not found")

            ordered_factors = table.ordered_factors()
            value_counts = [len(f.values) for f in ordered_factors]

            batch_end = min(job.cursor + request.batch_size, job.total_combinations)
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

            await db.combinations.bulk_insert(new_combinations)
            job.record_batch(new_cursor=batch_end, rows_created=len(new_combinations))
            await db.jobs.save(job)

            return GenerateCombinationsBatchResponse(job=job)

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

    async def get_generation_job(
        self, request: GetGenerationJobRequest
    ) -> GetGenerationJobResponse:
        async with self._database.snapshot() as db:
            job = await db.jobs.get(request.job_id)
            if job is None:
                raise NotFoundError(f"Generation job {request.job_id} not found")
            return GetGenerationJobResponse(job=job)

    async def list_stale_running_generation_jobs(
        self,
    ) -> ListStaleRunningGenerationJobsResponse:
        async with self._database.snapshot() as db:
            job_ids = await db.jobs_reader.list_stale_running()
            return ListStaleRunningGenerationJobsResponse(job_ids=job_ids)
