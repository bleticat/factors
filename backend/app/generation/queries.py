"""Read-side use cases for the `generation` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.generation.errors import GenerationJobNotFoundError
from app.generation.ports.generation_job_queries import (
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


@dataclass(frozen=True)
class ListStaleRunningGenerationJobsQuery(Query[list[int]]):
    pass


class ListStaleRunningGenerationJobsHandler:
    def __init__(self, queries: GenerationJobQueries) -> None:
        self._queries = queries

    async def handle(self, request: ListStaleRunningGenerationJobsQuery) -> list[int]:
        return await self._queries.list_stale_running()
