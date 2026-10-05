import pytest

from app.generation.use_cases import GenerationUseCases, RequestGenerationRequest
from app.shared.errors import InvariantViolationError
from app.tables.use_cases import (
    AddFactorRequest,
    AddFactorValueRequest,
    DeleteFactorRequest,
    TablesUseCases,
    UpdateFactorRequest,
)
from tests.helpers import (
    DEFAULT_TEST_MAX_COMBINATIONS,
    build_standard_table,
    generate_and_wait,
)


async def test_add_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    await GenerationUseCases(database).request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
    )  # leaves job 'pending'

    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="New factor")
        )


async def test_update_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await GenerationUseCases(database).request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
    )

    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).update_factor(
            UpdateFactorRequest(table_id=table_id, factor_id=browser_id, name="X")
        )


async def test_delete_factor_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await GenerationUseCases(database).request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
    )

    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).delete_factor(
            DeleteFactorRequest(table_id=table_id, factor_id=browser_id)
        )


async def test_add_factor_value_rejected_while_job_pending(database):
    fixture = await build_standard_table(database)
    table_id, browser_id = fixture["table_id"], fixture["browser_id"]
    await GenerationUseCases(database).request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
    )

    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(table_id=table_id, factor_id=browser_id, value="Edge")
        )


async def test_add_factor_succeeds_once_job_is_terminal(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    # Must not raise now that the job has completed.
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="New factor")
    )
