"""Spec 001 edge case: deleting a factor or factor value invalidates every
existing combination's signature, so it cascades deletion of all
combinations for that table — composes generation (spec 002) with a
structural mutation (spec 001), hence a workflow test."""

from app.combinations.use_cases import CombinationsUseCases
from app.tables.use_cases import TablesUseCases
from tests.helpers import build_standard_table, generate_and_wait


async def test_deleting_a_factor_removes_all_combinations_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    before = await CombinationsUseCases(database).list_combinations(table_id=table_id)
    assert before.total == 18

    await TablesUseCases(database).delete_factor(
        table_id=table_id, factor_id=fixture["browser_id"]
    )

    after = await CombinationsUseCases(database).list_combinations(table_id=table_id)
    assert after.total == 0


async def test_deleting_a_factor_value_removes_all_combinations_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    await TablesUseCases(database).delete_factor_value(
        table_id=table_id,
        factor_id=fixture["browser_id"],
        value_id=fixture["browser_values"][0],
    )

    after = await CombinationsUseCases(database).list_combinations(table_id=table_id)
    assert after.total == 0
