import pytest

from app.combinations.errors import (
    CombinationNotFoundError,
    InvalidCombinationStatusError,
)
from app.composition import build_combinations_commands, build_combinations_queries
from app.shared.execution import run_command, run_query
from tests.helpers import build_standard_table, generate_and_wait


async def _first_combination_id(database, table_id: int) -> int:

    page = await run_query(
        database,
        lambda scope: build_combinations_queries(scope).list_combinations(
            table_id=table_id
        ),
    )
    return page.items[0].id


async def test_patch_combination_sets_status_and_output(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)
    combination_id = await _first_combination_id(database, table_id)

    result = await run_command(
        database,
        lambda uow: build_combinations_commands(uow).patch_combination(
            table_id=table_id,
            combination_id=combination_id,
            status="possible",
            output="user reaches dashboard",
            output_set=True,
        ),
    )
    assert result.status == "possible"
    assert result.output == "user reaches dashboard"


async def test_patch_combination_sets_impossible_reason(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)
    combination_id = await _first_combination_id(database, table_id)

    result = await run_command(
        database,
        lambda uow: build_combinations_commands(uow).patch_combination(
            table_id=table_id,
            combination_id=combination_id,
            status="impossible",
            impossible_reason="not applicable",
            impossible_reason_set=True,
        ),
    )
    assert result.status == "impossible"
    assert result.impossible_reason == "not applicable"


async def test_patch_combination_rejects_invalid_status(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)
    combination_id = await _first_combination_id(database, table_id)

    with pytest.raises(InvalidCombinationStatusError):
        await run_command(
            database,
            lambda uow: build_combinations_commands(uow).patch_combination(
                table_id=table_id, combination_id=combination_id, status="bogus"
            ),
        )


async def test_patch_combination_from_a_different_table_raises_not_found(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    await generate_and_wait(database, fixture_a["table_id"])
    await generate_and_wait(database, fixture_b["table_id"])
    combination_from_a = await _first_combination_id(database, fixture_a["table_id"])

    with pytest.raises(CombinationNotFoundError):
        await run_command(
            database,
            lambda uow: build_combinations_commands(uow).patch_combination(
                table_id=fixture_b["table_id"],
                combination_id=combination_from_a,
                status="possible",
            ),
        )
