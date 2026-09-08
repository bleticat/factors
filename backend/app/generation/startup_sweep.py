"""Runs once at FastAPI lifespan startup, before serving traffic. Itself a
boundary — opens its own scopes like any other caller. No job can
legitimately be `running` right after a process start (generation runs
in-process via `BackgroundTasks`), so any such job was abandoned by the
previous process and is swept to `failed` (spec 002)."""

from __future__ import annotations

from app.composition import build_generation_commands, build_generation_queries
from app.shared.database.port import Database
from app.shared.execution import run_command, run_query

INTERRUPTED_MESSAGE = "Interrupted by server restart"


async def sweep_stale_generation_jobs(database: Database) -> int:
    stale_job_ids = await run_query(
        database,
        lambda scope: build_generation_queries(
            scope
        ).list_stale_running_generation_jobs(),
    )
    if not stale_job_ids:
        return 0
    return await run_command(
        database,
        lambda uow: build_generation_commands(uow).mark_stale_generation_jobs_failed(
            stale_job_ids, INTERRUPTED_MESSAGE
        ),
    )
