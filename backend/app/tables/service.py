"""Internal helper logic `tables.commands` delegates to. Not part of the
module's public request/response surface."""

from __future__ import annotations

from app.generation.errors import GenerationInProgressError
from app.generation.ports.generation_job_repository import GenerationJobRepository


async def ensure_not_generating(jobs: GenerationJobRepository, table_id: int) -> None:
    """Shared guard used by every factor/factor-value mutation command:
    reject if the table has a generation job in flight (see spec 001's
    "locked while generation running" rule and spec 002's cursor-stability
    rationale)."""
    if await jobs.has_active_job(table_id):
        raise GenerationInProgressError(table_id)
