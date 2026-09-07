from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.ports.generation_job_queries import GenerationJobQueries
from app.shared.mediator.requests import Query


@dataclass(frozen=True)
class ListStaleRunningGenerationJobsQuery(Query[list[int]]):
    pass


class ListStaleRunningGenerationJobsHandler:
    def __init__(self, queries: GenerationJobQueries) -> None:
        self._queries = queries

    async def handle(self, request: ListStaleRunningGenerationJobsQuery) -> list[int]:
        return await self._queries.list_stale_running()
