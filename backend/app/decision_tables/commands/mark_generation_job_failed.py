from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._job_refs import to_ref
from app.decision_tables.commands.results import GenerationJobRef
from app.decision_tables.domain.errors import GenerationJobNotFoundError
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class MarkGenerationJobFailedCommand(Command[GenerationJobRef]):
    job_id: int
    error_message: str


class MarkGenerationJobFailedHandler:
    def __init__(self, jobs: GenerationJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, request: MarkGenerationJobFailedCommand) -> GenerationJobRef:
        job = await self._jobs.get(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)
        job.fail(request.error_message)
        await self._jobs.save(job)
        return to_ref(job)
