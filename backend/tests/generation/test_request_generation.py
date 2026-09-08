import pytest

from app.combinations.queries import ListCombinationsQuery
from app.generation.commands import RequestGenerationCommand
from app.generation.errors import (
    CombinationCapExceededError,
    FactorHasNoValuesError,
    GenerationAlreadyInProgressError,
    NoFactorsError,
)
from tests.helpers import (
    add_factor_with_values,
    build_standard_table,
    create_table,
)


async def test_request_generation_computes_projected_total(mediator):
    fixture = await build_standard_table(mediator)
    job = await mediator.execute(RequestGenerationCommand(table_id=fixture["table_id"]))
    assert job.total_combinations == 18
    assert job.status == "pending"


async def test_request_generation_rejects_table_with_no_factors(mediator):
    table_id = await create_table(mediator)
    with pytest.raises(NoFactorsError):
        await mediator.execute(RequestGenerationCommand(table_id=table_id))


async def test_request_generation_rejects_factor_with_no_values(mediator):
    table_id = await create_table(mediator)
    from app.tables.commands import AddFactorCommand

    await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    with pytest.raises(FactorHasNoValuesError):
        await mediator.execute(RequestGenerationCommand(table_id=table_id))


async def test_request_generation_rejects_when_projection_exceeds_cap(low_cap_mediator):
    # low_cap_mediator caps at 10 combinations; 4x4 = 16 exceeds it.
    table_id = await create_table(low_cap_mediator)
    await add_factor_with_values(low_cap_mediator, table_id, "A", ["1", "2", "3", "4"])
    await add_factor_with_values(low_cap_mediator, table_id, "B", ["1", "2", "3", "4"])

    with pytest.raises(CombinationCapExceededError):
        await low_cap_mediator.execute(RequestGenerationCommand(table_id=table_id))

    # No combinations should have been created.
    page = await low_cap_mediator.execute(ListCombinationsQuery(table_id=table_id))
    assert page.total == 0


async def test_request_generation_rejects_second_request_while_first_in_flight(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await mediator.execute(RequestGenerationCommand(table_id=table_id))
    with pytest.raises(GenerationAlreadyInProgressError):
        await mediator.execute(RequestGenerationCommand(table_id=table_id))
