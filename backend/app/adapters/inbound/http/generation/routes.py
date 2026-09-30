"""Thin HTTP boundary: parse input, call the module's use cases, serialize
the result. The only exception is `request_generation`, which additionally
schedules the background batch loop — that loop is itself a boundary, not
a use-case method (see `generation/worker.py`)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.adapters.inbound.http.dependencies import get_database
from app.application.generation.use_cases import GenerationUseCases
from app.application.generation.worker import run_generation_job
from app.application.ports.database import Database
from app.config import settings

router = APIRouter()


def get_generation_use_cases(
    database: Database = Depends(get_database),
) -> GenerationUseCases:
    return GenerationUseCases(database)


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int,
    background_tasks: BackgroundTasks,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
    database: Database = Depends(get_database),
):
    job = await use_cases.request_generation(
        table_id, max_combinations=settings.max_combinations
    )
    background_tasks.add_task(
        run_generation_job,
        database=database,
        job_id=job.id,
        batch_size=settings.generation_batch_size,
    )
    return job


@router.get("/{table_id}/generation-jobs/{job_id}")
async def get_generation_job(
    table_id: int,
    job_id: int,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    return await use_cases.get_generation_job(job_id)


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int,
    job_id: int,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    return await use_cases.cancel_generation_job(job_id)
