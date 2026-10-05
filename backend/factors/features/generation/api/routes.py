from fastapi import APIRouter, BackgroundTasks, Depends, Request

from factors.config import settings
from factors.features.generation.use_cases import (
    CancelGenerationJobRequest,
    GenerationUseCases,
    GetGenerationJobRequest,
    RequestGenerationRequest,
)
from factors.features.generation.worker import run_generation_job

router = APIRouter()


def get_generation_use_cases(request: Request) -> GenerationUseCases:
    return GenerationUseCases(request.app.state.database)


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
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
    response = await use_cases.get_generation_job(GetGenerationJobRequest(job_id))
    return response.job


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int,
    job_id: int,
    use_cases: GenerationUseCases = Depends(get_generation_use_cases),
):
    response = await use_cases.cancel_generation_job(CancelGenerationJobRequest(job_id))
    return response.job
