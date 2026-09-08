"""Spec 001 edge case: deleting a factor or factor value invalidates every
existing combination's signature, so it cascades deletion of all
combinations for that table — composes generation (spec 002) with a
structural mutation (spec 001), hence a workflow test."""

from app.composition import build_combinations_queries, build_tables_commands
from app.shared.execution import run_command, run_query
from tests.helpers import build_standard_table, generate_and_wait


async def test_deleting_a_factor_removes_all_combinations_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    before = await run_query(
        database,
        lambda scope: build_combinations_queries(scope).list_combinations(
            table_id=table_id
        ),
    )
    assert before.total == 18

    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_factor(
            table_id=table_id, factor_id=fixture["browser_id"]
        ),
    )

    after = await run_query(
        database,
        lambda scope: build_combinations_queries(scope).list_combinations(
            table_id=table_id
        ),
    )
    assert after.total == 0


async def test_deleting_a_factor_value_removes_all_combinations_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_factor_value(
            table_id=table_id,
            factor_id=fixture["browser_id"],
            value_id=fixture["browser_values"][0],
        ),
    )

    after = await run_query(
        database,
        lambda scope: build_combinations_queries(scope).list_combinations(
            table_id=table_id
        ),
    )
    assert after.total == 0
