"""Runs once at FastAPI lifespan startup, before serving traffic. Itself a
boundary — builds its own use cases from the `Database`, like any other
caller. No job can legitimately be `running` right after a process start
(generation runs in-process via `BackgroundTasks`), so any such job was
abandoned by the previous process and is swept to `failed` (spec 002)."""

from __future__ import annotations

from app.generation.use_cases import GenerationUseCases
from app.shared.ports.database import Database

INTERRUPTED_MESSAGE = "Interrupted by server restart"


async def sweep_stale_generation_jobs(database: Database) -> int:
    """Mark any job left `running` by a previous process as `failed`.
    Returns how many jobs were swept."""
    use_cases = GenerationUseCases(database)
    stale_job_ids = await use_cases.list_stale_running_generation_jobs()
    if not stale_job_ids:
        return 0
    return await use_cases.mark_stale_generation_jobs_failed(
        stale_job_ids, INTERRUPTED_MESSAGE
    )
