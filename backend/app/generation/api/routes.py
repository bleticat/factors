"""Thin HTTP boundary: parse input, submit a typed request to the mediator,
serialize the result (ADR 007). The only exception is `request_generation`,
which additionally schedules the background batch loop — that loop is
itself a boundary, not a handler (see `generation/worker.py`)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.config import settings
from app.generation.commands import CancelGenerationJobCommand, RequestGenerationCommand
from app.generation.queries import GetGenerationJobQuery
from app.generation.worker import run_generation_job
from app.shared.api import get_mediator
from app.shared.mediator.mediator import Mediator

router = APIRouter()


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int, background_tasks: BackgroundTasks, mediator: Mediator = Depends(get_mediator)
):
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    background_tasks.add_task(
        run_generation_job,
        mediator=mediator,
        job_id=job.id,
        batch_size=settings.generation_batch_size,
    )
    return job


@router.get("/{table_id}/generation-jobs/{job_id}")
async def get_generation_job(
    table_id: int, job_id: int, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(GetGenerationJobQuery(job_id=job_id))


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int, job_id: int, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(CancelGenerationJobCommand(job_id=job_id))
