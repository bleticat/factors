"""Shared guard used by every factor/factor-value mutation command: reject
if the table has a generation job in flight (see spec 001's "locked while
generation running" rule and spec 002's cursor-stability rationale)."""

from __future__ import annotations

from app.decision_tables.domain.errors import GenerationInProgressError
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository


async def ensure_not_generating(jobs: GenerationJobRepository, table_id: int) -> None:
    if await jobs.has_active_job(table_id):
        raise GenerationInProgressError(table_id)
