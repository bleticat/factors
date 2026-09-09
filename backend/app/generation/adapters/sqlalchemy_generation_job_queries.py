from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import GenerationJobStatus
from app.generation.ports.generation_job_queries import (
    GenerationJobDTO,
    GenerationJobQueries,
)


class SqlAlchemyGenerationJobQueries(GenerationJobQueries):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_stale_running(self) -> list[int]:
        async with self._session_factory() as session:
            stmt = select(GenerationJobRow.id).where(
                GenerationJobRow.status == str(GenerationJobStatus.RUNNING)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def get(self, job_id: int) -> GenerationJobDTO | None:
        async with self._session_factory() as session:
            row = await session.get(GenerationJobRow, job_id)
            if row is None:
                return None
            return GenerationJobDTO(
                id=row.id,
                decision_table_id=row.decision_table_id,
                status=row.status,
                total_combinations=row.total_combinations,
                created_count=row.created_count,
                error_message=row.error_message,
            )
