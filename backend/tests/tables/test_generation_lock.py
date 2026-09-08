"""Spec 001's "locked while generation running" rule: factor/value mutation
commands are rejected while a generation job is pending/running, and
succeed again once the job reaches a terminal state."""

import pytest

from app.generation.commands import RequestGenerationCommand
from app.generation.errors import GenerationInProgressError
from app.tables.commands import (
    AddFactorCommand,
    AddFactorValueCommand,
    DeleteFactorCommand,
    UpdateFactorCommand,
)
from tests.helpers import build_standard_table, generate_and_wait


async def test_add_factor_rejected_while_job_pending(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]

    await mediator.execute(RequestGenerationCommand(table_id=table_id))  # leaves job 'pending'

    with pytest.raises(GenerationInProgressError):
        await mediator.execute(AddFactorCommand(table_id=table_id, name="New factor"))


async def test_update_factor_rejected_while_job_pending(mediator):
    fixture = await build_standard_table(mediator)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await mediator.execute(RequestGenerationCommand(table_id=table_id))

    with pytest.raises(GenerationInProgressError):
        await mediator.execute(UpdateFactorCommand(table_id=table_id, factor_id=browser_id, name="X"))


async def test_delete_factor_rejected_while_job_pending(mediator):
    fixture = await build_standard_table(mediator)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await mediator.execute(RequestGenerationCommand(table_id=table_id))

    with pytest.raises(GenerationInProgressError):
        await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=browser_id))


async def test_add_factor_value_rejected_while_job_pending(mediator):
    fixture = await build_standard_table(mediator)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await mediator.execute(RequestGenerationCommand(table_id=table_id))

    with pytest.raises(GenerationInProgressError):
        await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=browser_id, value="Edge"))


async def test_add_factor_succeeds_once_job_is_terminal(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    # Must not raise now that the job has completed.
    await mediator.execute(AddFactorCommand(table_id=table_id, name="New factor"))
