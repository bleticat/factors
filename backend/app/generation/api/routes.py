"""Thin HTTP boundary: parse input, call the module's command/query
service, serialize the result. The only exception is `request_generation`,
which additionally schedules the background batch loop — that loop is
itself a boundary, not a use-case method (see `generation/worker.py`)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from app.composition import build_generation_commands, build_generation_queries
from app.config import settings
from app.generation.commands import GenerationCommands
from app.generation.queries import GenerationQueries
from app.generation.worker import run_generation_job
from app.shared.api import get_database, get_read_scope, get_uow
from app.shared.database.port import Database, ReadScope, UnitOfWork

router = APIRouter()


def get_generation_commands(uow: UnitOfWork = Depends(get_uow)) -> GenerationCommands:
    return build_generation_commands(uow)


def get_generation_queries(
    scope: ReadScope = Depends(get_read_scope),
) -> GenerationQueries:
    return build_generation_queries(scope)


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int,
    background_tasks: BackgroundTasks,
    commands: GenerationCommands = Depends(get_generation_commands),
    database: Database = Depends(get_database),
):
    job = await commands.request_generation(
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
    queries: GenerationQueries = Depends(get_generation_queries),
):
    return await queries.get_generation_job(job_id)


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int,
    job_id: int,
    commands: GenerationCommands = Depends(get_generation_commands),
):
    return await commands.cancel_generation_job(job_id)
