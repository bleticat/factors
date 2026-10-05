from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.adapters.orm import GenerationJobRow
from app.generation.entities import GenerationJobStatus
from app.generation.ports.generation_job_reader import GenerationJobReader


class SqlAlchemyGenerationJobReader(GenerationJobReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_stale_running(self) -> list[int]:
        stmt = select(GenerationJobRow.id).where(
            GenerationJobRow.status == str(GenerationJobStatus.RUNNING)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
