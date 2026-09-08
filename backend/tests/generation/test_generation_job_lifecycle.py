import pytest

from app.generation.commands import (
    CancelGenerationJobCommand,
    GenerateCombinationsBatchCommand,
    MarkGenerationJobFailedCommand,
    MarkStaleGenerationJobsFailedCommand,
    RequestGenerationCommand,
)
from app.generation.errors import (
    GenerationJobNotFoundError,
    InvalidGenerationJobTransitionError,
)
from app.generation.queries import (
    GetGenerationJobQuery,
    ListStaleRunningGenerationJobsQuery,
)
from tests.helpers import build_standard_table, generate_and_wait


async def test_cancel_pending_job_transitions_to_cancelled(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))

    cancelled = await mediator.execute(CancelGenerationJobCommand(job_id=job.id))
    assert cancelled.status == "cancelled"


async def test_cancel_stops_further_batches_from_creating_rows(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))

    # Advance one batch (partial progress), then cancel.
    await mediator.execute(GenerateCombinationsBatchCommand(job_id=job.id, batch_size=5))
    await mediator.execute(CancelGenerationJobCommand(job_id=job.id))

    # The batch loop, on observing 'cancelled', should stop without
    # inserting more — simulate by calling the batch command again.
    result = await mediator.execute(GenerateCombinationsBatchCommand(job_id=job.id, batch_size=5))
    assert result.status == "cancelled"
    assert result.created_count == 5  # unchanged from before cancellation


async def test_cancel_already_terminal_job_raises(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(mediator, table_id)

    with pytest.raises(InvalidGenerationJobTransitionError):
        await mediator.execute(CancelGenerationJobCommand(job_id=completed.id))


async def test_mark_generation_job_failed_records_error_message(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))

    failed = await mediator.execute(
        MarkGenerationJobFailedCommand(job_id=job.id, error_message="boom")
    )
    assert failed.status == "failed"
    assert failed.error_message == "boom"

    fetched = await mediator.execute(GetGenerationJobQuery(job_id=job.id))
    assert fetched.status == "failed"
    assert fetched.error_message == "boom"


async def test_mark_generation_job_failed_against_missing_job_raises(mediator):
    with pytest.raises(GenerationJobNotFoundError):
        await mediator.execute(MarkGenerationJobFailedCommand(job_id=999, error_message="x"))


async def test_stale_running_jobs_are_swept_to_failed(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    # One partial batch transitions pending -> running without completing
    # (18 total, batch of 5 leaves it running).
    partial = await mediator.execute(GenerateCombinationsBatchCommand(job_id=job.id, batch_size=5))
    assert partial.status == "running"

    stale_ids = await mediator.execute(ListStaleRunningGenerationJobsQuery())
    assert job.id in stale_ids

    updated_count = await mediator.execute(
        MarkStaleGenerationJobsFailedCommand(job_ids=stale_ids, error_message="Interrupted by server restart")
    )
    assert updated_count == len(stale_ids)

    fetched = await mediator.execute(GetGenerationJobQuery(job_id=job.id))
    assert fetched.status == "failed"
    assert fetched.error_message == "Interrupted by server restart"
    assert fetched.created_count == 5  # partial progress preserved, not reset


async def test_sweep_does_not_touch_non_running_jobs(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(mediator, table_id)

    stale_ids = await mediator.execute(ListStaleRunningGenerationJobsQuery())
    assert completed.id not in stale_ids
