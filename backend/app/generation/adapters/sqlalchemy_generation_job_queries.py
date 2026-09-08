from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import GenerationJobStatus
from app.generation.ports.generation_job_queries import (
    GenerationJobDTO,
    GenerationJobQueries,
)
from app.shared.database.sqlalchemy_database import SqlAlchemyReadScope


class SqlAlchemyGenerationJobQueries(GenerationJobQueries):
    def __init__(self, scope: SqlAlchemyReadScope) -> None:
        self._session: AsyncSession = scope.session

    async def list_stale_running(self) -> list[int]:
        stmt = select(GenerationJobRow.id).where(
            GenerationJobRow.status == str(GenerationJobStatus.RUNNING)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get(self, job_id: int) -> GenerationJobDTO | None:
        row = await self._session.get(GenerationJobRow, job_id)
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
