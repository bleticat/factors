import pytest

from app.application.combinations.use_cases import CombinationsUseCases
from app.application.generation.use_cases import GenerationUseCases
from app.application.tables.use_cases import TablesUseCases
from app.domain.generation.errors import (
    CombinationCapExceededError,
    FactorHasNoValuesError,
    GenerationAlreadyInProgressError,
    NoFactorsError,
)
from tests.helpers import (
    DEFAULT_TEST_MAX_COMBINATIONS,
    add_factor_with_values,
    build_standard_table,
    create_table,
)


async def test_request_generation_computes_projected_total(database):
    fixture = await build_standard_table(database)
    job = await GenerationUseCases(database).request_generation(
        table_id=fixture["table_id"], max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
    )
    assert job.total_combinations == 18
    assert job.status == "pending"


async def test_request_generation_rejects_table_with_no_factors(database):
    table_id = await create_table(database)
    with pytest.raises(NoFactorsError):
        await GenerationUseCases(database).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )


async def test_request_generation_rejects_factor_with_no_values(database):
    table_id = await create_table(database)

    await TablesUseCases(database).add_factor(table_id=table_id, name="Browser")
    with pytest.raises(FactorHasNoValuesError):
        await GenerationUseCases(database).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )


async def test_request_generation_rejects_when_projection_exceeds_cap(database):
    # max_combinations=10 below caps it; 4x4 = 16 exceeds that.
    table_id = await create_table(database)
    await add_factor_with_values(database, table_id, "A", ["1", "2", "3", "4"])
    await add_factor_with_values(database, table_id, "B", ["1", "2", "3", "4"])

    with pytest.raises(CombinationCapExceededError):
        await GenerationUseCases(database).request_generation(
            table_id=table_id, max_combinations=10
        )

    # No combinations should have been created.
    page = await CombinationsUseCases(database).list_combinations(table_id=table_id)
    assert page.total == 0


async def test_request_generation_rejects_second_request_while_first_in_flight(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await GenerationUseCases(database).request_generation(
        table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
    )
    with pytest.raises(GenerationAlreadyInProgressError):
        await GenerationUseCases(database).request_generation(
            table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
        )
