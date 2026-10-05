"""Thin HTTP boundary: parse input, call the module's use cases, serialize
the result. The only exception is `request_generation`, which additionally
schedules the background batch loop — that loop is itself a boundary, not
a use-case method (see `generation/worker.py`)."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.config import settings
from app.generation.use_cases import (
    CancelGenerationJobRequest,
    GenerationUseCases,
    GetGenerationJobRequest,
    RequestGenerationRequest,
)
from app.generation.worker import run_generation_job

router = APIRouter()


def get_generation_use_cases(request: Request) -> GenerationUseCases:
    """FastAPI dependency: build a `GenerationUseCases` for the current request."""
    return GenerationUseCases(request.app.state.database)


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    """Start generating combinations for a decision table and schedule the
    background batch loop that drives the job to completion."""
    response = await use_cases.request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=settings.max_combinations
        )
    )
    background_tasks.add_task(
        run_generation_job,
        database=request.app.state.database,
        job_id=response.job.id,
        batch_size=settings.generation_batch_size,
    )
    return response.job


@router.get("/{table_id}/generation-jobs/{job_id}")
async def get_generation_job(
    table_id: int,
    job_id: int,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    """Get a generation job's current status and progress."""
    response = await use_cases.get_generation_job(GetGenerationJobRequest(job_id))
    return response.job


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int,
    job_id: int,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    """Cancel an active generation job."""
    response = await use_cases.cancel_generation_job(CancelGenerationJobRequest(job_id))
    return response.job
