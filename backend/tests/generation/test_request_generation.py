import pytest

from factors.features.combinations.use_cases import (
    CombinationsUseCases,
    ListCombinationsRequest,
)
from factors.features.generation.use_cases import (
    GenerationUseCases,
    RequestGenerationRequest,
)
from factors.features.tables.use_cases import AddFactorRequest, TablesUseCases
from factors.shared.errors import InvariantViolationError
from tests.helpers import (
    DEFAULT_TEST_MAX_COMBINATIONS,
    add_factor_with_values,
    build_standard_table,
    create_table,
)


async def test_request_generation_computes_projected_total(database):
    fixture = await build_standard_table(database)
    job = (
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=fixture["table_id"],
                max_combinations=DEFAULT_TEST_MAX_COMBINATIONS,
            )
        )
    ).job
    assert job.total_combinations == 18
    assert job.status == "pending"


async def test_request_generation_rejects_table_with_no_factors(database):
    table_id = await create_table(database)
    with pytest.raises(InvariantViolationError):
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
            )
        )


async def test_request_generation_rejects_factor_with_no_values(database):
    table_id = await create_table(database)

    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="Browser")
    )
    with pytest.raises(InvariantViolationError):
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
            )
        )


async def test_request_generation_rejects_when_projection_exceeds_cap(database):
    # max_combinations=10 below caps it; 4x4 = 16 exceeds that.
    table_id = await create_table(database)
    await add_factor_with_values(database, table_id, "A", ["1", "2", "3", "4"])
    await add_factor_with_values(database, table_id, "B", ["1", "2", "3", "4"])

    with pytest.raises(InvariantViolationError):
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(table_id=table_id, max_combinations=10)
        )

    # No combinations should have been created.
    page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(table_id=table_id)
        )
    ).page
    assert page.total == 0


async def test_request_generation_rejects_second_request_while_first_in_flight(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await GenerationUseCases(database).request_generation(
        RequestGenerationRequest(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
    )
    with pytest.raises(InvariantViolationError):
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
            )
        )
