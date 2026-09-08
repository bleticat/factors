import pytest

from app.composition import build_generation_commands, build_generation_queries
from app.generation.errors import (
    GenerationJobNotFoundError,
    InvalidGenerationJobTransitionError,
)
from app.shared.execution import run_command, run_query
from tests.helpers import (
    DEFAULT_TEST_MAX_COMBINATIONS,
    build_standard_table,
    generate_and_wait,
)


async def test_cancel_pending_job_transitions_to_cancelled(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    job = await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    cancelled = await run_command(
        database,
        lambda uow: build_generation_commands(uow).cancel_generation_job(job_id=job.id),
    )
    assert cancelled.status == "cancelled"


async def test_cancel_stops_further_batches_from_creating_rows(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    job = await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    # Advance one batch (partial progress), then cancel.
    await run_command(
        database,
        lambda uow: build_generation_commands(uow).generate_combinations_batch(
            job_id=job.id, batch_size=5
        ),
    )
    await run_command(
        database,
        lambda uow: build_generation_commands(uow).cancel_generation_job(job_id=job.id),
    )

    # The batch loop, on observing 'cancelled', should stop without
    # inserting more — simulate by calling the batch command again.
    result = await run_command(
        database,
        lambda uow: build_generation_commands(uow).generate_combinations_batch(
            job_id=job.id, batch_size=5
        ),
    )
    assert result.status == "cancelled"
    assert result.created_count == 5  # unchanged from before cancellation


async def test_cancel_already_terminal_job_raises(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(database, table_id)

    with pytest.raises(InvalidGenerationJobTransitionError):
        await run_command(
            database,
            lambda uow: build_generation_commands(uow).cancel_generation_job(
                job_id=completed.id
            ),
        )


async def test_mark_generation_job_failed_records_error_message(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    job = await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    failed = await run_command(
        database,
        lambda uow: build_generation_commands(uow).mark_generation_job_failed(
            job_id=job.id, error_message="boom"
        ),
    )
    assert failed.status == "failed"
    assert failed.error_message == "boom"

    fetched = await run_query(
        database,
        lambda scope: build_generation_queries(scope).get_generation_job(job_id=job.id),
    )
    assert fetched.status == "failed"
    assert fetched.error_message == "boom"


async def test_mark_generation_job_failed_against_missing_job_raises(database):
    with pytest.raises(GenerationJobNotFoundError):
        await run_command(
            database,
            lambda uow: build_generation_commands(uow).mark_generation_job_failed(
                job_id=999, error_message="x"
            ),
        )


async def test_stale_running_jobs_are_swept_to_failed(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    job = await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )
    # One partial batch transitions pending -> running without completing
    # (18 total, batch of 5 leaves it running).
    partial = await run_command(
        database,
        lambda uow: build_generation_commands(uow).generate_combinations_batch(
            job_id=job.id, batch_size=5
        ),
    )
    assert partial.status == "running"

    stale_ids = await run_query(
        database,
        lambda scope: build_generation_queries(
            scope
        ).list_stale_running_generation_jobs(),
    )
    assert job.id in stale_ids

    updated_count = await run_command(
        database,
        lambda uow: build_generation_commands(uow).mark_stale_generation_jobs_failed(
            job_ids=stale_ids, error_message="Interrupted by server restart"
        ),
    )
    assert updated_count == len(stale_ids)

    fetched = await run_query(
        database,
        lambda scope: build_generation_queries(scope).get_generation_job(job_id=job.id),
    )
    assert fetched.status == "failed"
    assert fetched.error_message == "Interrupted by server restart"
    assert fetched.created_count == 5  # partial progress preserved, not reset


async def test_sweep_does_not_touch_non_running_jobs(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(database, table_id)

    stale_ids = await run_query(
        database,
        lambda scope: build_generation_queries(
            scope
        ).list_stale_running_generation_jobs(),
    )
    assert completed.id not in stale_ids
