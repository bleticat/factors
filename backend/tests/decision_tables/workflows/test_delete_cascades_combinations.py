"""Spec 001 edge case: deleting a factor or factor value invalidates every
existing combination's signature, so it cascades deletion of all
combinations for that table — composes generation (spec 002) with a
structural mutation (spec 001), hence a workflow test."""

from app.decision_tables.commands.delete_factor import DeleteFactorCommand
from app.decision_tables.commands.delete_factor_value import DeleteFactorValueCommand
from app.decision_tables.queries.list_combinations import ListCombinationsQuery
from tests.decision_tables.helpers import build_standard_table, generate_and_wait


async def test_deleting_a_factor_removes_all_combinations_for_the_table(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    before = await mediator.execute(ListCombinationsQuery(table_id=table_id))
    assert before.total == 18

    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=fixture["browser_id"]))

    after = await mediator.execute(ListCombinationsQuery(table_id=table_id))
    assert after.total == 0


async def test_deleting_a_factor_value_removes_all_combinations_for_the_table(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    await mediator.execute(
        DeleteFactorValueCommand(
            table_id=table_id, factor_id=fixture["browser_id"], value_id=fixture["browser_values"][0]
        )
    )

    after = await mediator.execute(ListCombinationsQuery(table_id=table_id))
    assert after.total == 0
