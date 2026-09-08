import pytest

from app.composition import build_tables_commands, build_tables_queries
from app.shared.errors import EmptyNameError
from app.shared.execution import run_command, run_query
from app.tables.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorNameError,
    FactorNotFoundError,
)
from tests.helpers import create_table


async def test_add_factor_appends_with_incrementing_order_index(database):
    table_id = await create_table(database)
    first = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    second = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(table_id=table_id, name="OS"),
    )
    assert first.order_index == 0
    assert second.order_index == 1

    table = await run_query(
        database,
        lambda scope: build_tables_queries(scope).get_decision_table(table_id=table_id),
    )
    assert [f.name for f in table.factors] == ["Browser", "OS"]


async def test_add_factor_rejects_empty_name(database):
    table_id = await create_table(database)
    with pytest.raises(EmptyNameError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor(
                table_id=table_id, name="  "
            ),
        )


async def test_add_factor_rejects_duplicate_name_within_table(database):
    table_id = await create_table(database)
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    with pytest.raises(DuplicateFactorNameError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor(
                table_id=table_id, name="Browser"
            ),
        )


async def test_add_factor_allows_same_name_in_different_table(database):
    table_a = await create_table(database, name="A")
    table_b = await create_table(database, name="B")
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_a, name="Browser"
        ),
    )
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_b, name="Browser"
        ),
    )  # must not raise


async def test_add_factor_against_missing_table_raises(database):
    with pytest.raises(DecisionTableNotFoundError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor(
                table_id=999, name="Browser"
            ),
        )


async def test_update_factor_renames_without_disturbing_order_index(database):
    table_id = await create_table(database)
    factor = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    updated = await run_command(
        database,
        lambda uow: build_tables_commands(uow).update_factor(
            table_id=table_id, factor_id=factor.id, name="Web Browser"
        ),
    )
    assert updated.name == "Web Browser"
    assert updated.order_index == factor.order_index


async def test_update_factor_against_factor_in_different_table_raises_not_found(
    database,
):
    table_a = await create_table(database, name="A")
    table_b = await create_table(database, name="B")
    factor = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_a, name="Browser"
        ),
    )
    with pytest.raises(FactorNotFoundError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).update_factor(
                table_id=table_b, factor_id=factor.id, name="X"
            ),
        )


async def test_delete_factor_removes_it_and_its_values(database):
    table_id = await create_table(database)
    factor = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_factor(
            table_id=table_id, factor_id=factor.id
        ),
    )
    table = await run_query(
        database,
        lambda scope: build_tables_queries(scope).get_decision_table(table_id=table_id),
    )
    assert table.factors == []


async def test_delete_factor_does_not_affect_other_factors(database):
    table_id = await create_table(database)
    browser = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(table_id=table_id, name="OS"),
    )
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_factor(
            table_id=table_id, factor_id=browser.id
        ),
    )

    table = await run_query(
        database,
        lambda scope: build_tables_queries(scope).get_decision_table(table_id=table_id),
    )
    assert [f.name for f in table.factors] == ["OS"]
