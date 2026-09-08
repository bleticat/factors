"""Spec 001's "locked while generation running" rule: factor/value mutation
commands are rejected while a generation job is pending/running, and
succeed again once the job reaches a terminal state."""

import pytest

from app.composition import build_generation_commands, build_tables_commands
from app.generation.errors import GenerationInProgressError
from app.shared.execution import run_command
from tests.helpers import (
    DEFAULT_TEST_MAX_COMBINATIONS,
    build_standard_table,
    generate_and_wait,
)


async def test_add_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )  # leaves job 'pending'

    with pytest.raises(GenerationInProgressError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor(
                table_id=table_id, name="New factor"
            ),
        )


async def test_update_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    with pytest.raises(GenerationInProgressError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).update_factor(
                table_id=table_id, factor_id=browser_id, name="X"
            ),
        )


async def test_delete_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    with pytest.raises(GenerationInProgressError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).delete_factor(
                table_id=table_id, factor_id=browser_id
            ),
        )


async def test_add_factor_value_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await run_command(
        database,
        lambda uow: build_generation_commands(uow).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        ),
    )

    with pytest.raises(GenerationInProgressError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor_value(
                table_id=table_id, factor_id=browser_id, value="Edge"
            ),
        )


async def test_add_factor_succeeds_once_job_is_terminal(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    # Must not raise now that the job has completed.
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="New factor"
        ),
    )
