from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import GenerationJobStatus
from app.generation.ports.generation_job_reader import (
    GenerationJobDTO,
    GenerationJobReader,
)


class SqlAlchemyGenerationJobReader(GenerationJobReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_stale_running(self) -> list[int]:
        """Ids of all jobs currently in `running` status (used by the
        startup sweep — none can legitimately survive a process restart)."""
        stmt = select(GenerationJobRow.id).where(
            GenerationJobRow.status == str(GenerationJobStatus.RUNNING)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get(self, job_id: int) -> GenerationJobDTO | None:
        """Return a job's current status and progress, or None if
        `job_id` doesn't exist."""
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
