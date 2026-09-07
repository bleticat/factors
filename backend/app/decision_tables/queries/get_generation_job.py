from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.domain.errors import GenerationJobNotFoundError
from app.decision_tables.ports.generation_job_queries import (
    GenerationJobDTO,
    GenerationJobQueries,
)
from app.shared.mediator.requests import Query


@dataclass(frozen=True)
class GetGenerationJobQuery(Query[GenerationJobDTO]):
    job_id: int


class GetGenerationJobHandler:
    def __init__(self, queries: GenerationJobQueries) -> None:
        self._queries = queries

    async def handle(self, request: GetGenerationJobQuery) -> GenerationJobDTO:
        job = await self._queries.get(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)
        return job
