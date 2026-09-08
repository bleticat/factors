"""Read-side use cases for the `generation` module."""

from __future__ import annotations

from app.generation.errors import GenerationJobNotFoundError
from app.generation.ports.generation_job_queries import (
    GenerationJobDTO,
    GenerationJobQueries,
)


class GenerationQueries:
    """The `generation` module's read-side use cases. Built per call by
    `app.composition.build_generation_queries`."""

    def __init__(self, jobs: GenerationJobQueries) -> None:
        self._jobs = jobs

    async def get_generation_job(self, job_id: int) -> GenerationJobDTO:
        job = await self._jobs.get(job_id)
        if job is None:
            raise GenerationJobNotFoundError(job_id)
        return job

    async def list_stale_running_generation_jobs(self) -> list[int]:
        return await self._jobs.list_stale_running()
