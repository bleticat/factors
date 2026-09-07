"""Runs once at FastAPI lifespan startup, before serving traffic. Itself a
boundary — dispatches through the mediator like any other caller. No job can
legitimately be `running` right after a process start (generation runs
in-process via `BackgroundTasks`), so any such job was abandoned by the
previous process and is swept to `failed` (spec 002)."""

from __future__ import annotations

from app.decision_tables.commands.mark_stale_generation_jobs_failed import (
    MarkStaleGenerationJobsFailedCommand,
)
from app.decision_tables.queries.list_stale_running_generation_jobs import (
    ListStaleRunningGenerationJobsQuery,
)
from app.shared.mediator.mediator import Mediator

INTERRUPTED_MESSAGE = "Interrupted by server restart"


async def sweep_stale_generation_jobs(mediator: Mediator) -> int:
    stale_job_ids = await mediator.execute(ListStaleRunningGenerationJobsQuery())
    if not stale_job_ids:
        return 0
    return await mediator.execute(
        MarkStaleGenerationJobsFailedCommand(job_ids=stale_job_ids, error_message=INTERRUPTED_MESSAGE)
    )
