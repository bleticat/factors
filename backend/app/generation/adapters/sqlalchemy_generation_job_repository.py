from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import ACTIVE_STATUSES, GenerationJob, GenerationJobStatus
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.shared.database.sqlalchemy_database import SqlAlchemyUnitOfWork


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
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._session: AsyncSession = uow.session

    async def add(self, job: GenerationJob) -> GenerationJob:
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
        row = await self._session.get(GenerationJobRow, job_id)
        return None if row is None else _to_domain(row)

    async def get_for_update(self, job_id: int) -> GenerationJob | None:
        # SQLite has no row-level SELECT ... FOR UPDATE; the single-writer
        # transaction model plus reading fresh within this command's own
        # unit of work is what gives GenerateCombinationsBatchCommand a
        # consistent view of live status/cursor (see ADR 004/007 + the
        # generation feature spec).
        return await self.get(job_id)

    async def save(self, job: GenerationJob) -> None:
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
        stmt = select(GenerationJobRow.id).where(
            GenerationJobRow.decision_table_id == table_id,
            GenerationJobRow.status.in_([str(s) for s in ACTIVE_STATUSES]),
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def mark_failed_bulk(self, job_ids: list[int], error_message: str) -> int:
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
