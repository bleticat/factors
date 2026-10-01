from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import ACTIVE_STATUSES, GenerationJob, GenerationJobStatus
from app.generation.ports.generation_job_repository import GenerationJobRepository


def _to_domain(row: GenerationJobRow) -> GenerationJob:
    return GenerationJob(
        id=row.id,
        decision_table_id=row.decision_table_id,
        status=GenerationJobStatus(row.status),
        total_combinations=row.total_combinations,
        created_count=row.created_count,
        cursor=row.cursor,
        error_message=row.error_message,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


class SqlAlchemyGenerationJobRepository(GenerationJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: GenerationJob) -> GenerationJob:
        """Insert a new job and populate its generated `id` in place."""
        row = GenerationJobRow(
            decision_table_id=job.decision_table_id,
            status=str(job.status),
            total_combinations=job.total_combinations,
            created_count=job.created_count,
            cursor=job.cursor,
        )
        self._session.add(row)
        await self._session.flush()
        job.id = row.id
        return job

    async def get(self, job_id: int) -> GenerationJob | None:
        """Return a job, or None if `job_id` doesn't exist."""
        row = await self._session.get(GenerationJobRow, job_id)
        return None if row is None else _to_domain(row)

    async def get_for_update(self, job_id: int) -> GenerationJob | None:
        """Like `get`, but the caller intends to mutate and `save` within
        the same transaction — read fresh, not from any cache."""
        # SQLite has no row-level SELECT ... FOR UPDATE; the single-writer
        # transaction model plus reading fresh within this command's own
        # unit of work is what gives GenerateCombinationsBatchCommand a
        # consistent view of live status/cursor (see ADR 004/007 + the
        # generation feature spec).
        return await self.get(job_id)

    async def save(self, job: GenerationJob) -> None:
        """Persist a job's current status/progress fields."""
        assert job.id is not None
        row = await self._session.get(GenerationJobRow, job.id)
        assert row is not None
        row.status = str(job.status)
        row.total_combinations = job.total_combinations
        row.created_count = job.created_count
        row.cursor = job.cursor
        row.error_message = job.error_message
        row.started_at = job.started_at
        row.finished_at = job.finished_at
        await self._session.flush()

    async def has_active_job(self, table_id: int) -> bool:
        """True if `table_id` has a job in `pending` or `running` status."""
        stmt = select(GenerationJobRow.id).where(
            GenerationJobRow.decision_table_id == table_id,
            GenerationJobRow.status.in_([str(s) for s in ACTIVE_STATUSES]),
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def mark_failed_bulk(self, job_ids: list[int], error_message: str) -> int:
        """Set-based transition of `running` jobs to `failed`. Returns the
        number of rows updated."""
        if not job_ids:
            return 0
        stmt = (
            update(GenerationJobRow)
            .where(GenerationJobRow.id.in_(job_ids))
            .values(status=str(GenerationJobStatus.FAILED), error_message=error_message)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
