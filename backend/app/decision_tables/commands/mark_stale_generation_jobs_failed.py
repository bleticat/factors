from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class MarkStaleGenerationJobsFailedCommand(Command[int]):
    job_ids: list[int] = field(default_factory=list)
    error_message: str = "Interrupted by server restart"


class MarkStaleGenerationJobsFailedHandler:
    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, request: MarkStaleGenerationJobsFailedCommand) -> int:
        return await self._jobs.mark_failed_bulk(request.job_ids, request.error_message)
