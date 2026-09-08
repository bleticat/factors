import pytest

from app.composition import build_tables_commands, build_tables_queries
from app.shared.errors import EmptyNameError
from app.shared.execution import run_command, run_query
from app.tables.errors import DecisionTableNotFoundError
from tests.helpers import create_table


async def test_create_decision_table_succeeds(database):
    ref = await run_command(
        database,
        lambda uow: build_tables_commands(uow).create_decision_table(
            name="Login flow", description="desc"
        ),
    )
    assert ref.name == "Login flow"
    assert ref.description == "desc"

    table = await run_query(
        database,
        lambda scope: build_tables_queries(scope).get_decision_table(table_id=ref.id),
    )
    assert table.name == "Login flow"
    assert table.factors == []


async def test_create_decision_table_rejects_empty_name(database):
    with pytest.raises(EmptyNameError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).create_decision_table(name="   "),
        )


async def test_update_decision_table_renames_and_redescribes(database):
    table_id = await create_table(database, name="Old", description="old desc")
    updated = await run_command(
        database,
        lambda uow: build_tables_commands(uow).update_decision_table(
            table_id=table_id, name="New", description="new desc", description_set=True
        ),
    )
    assert updated.name == "New"
    assert updated.description == "new desc"


async def test_update_decision_table_against_missing_table_raises(database):
    with pytest.raises(DecisionTableNotFoundError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).update_decision_table(
                table_id=999, name="X"
            ),
        )


async def test_delete_decision_table_then_get_raises_not_found(database):
    table_id = await create_table(database)
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_decision_table(table_id=table_id),
    )
    with pytest.raises(DecisionTableNotFoundError):
        await run_query(
            database,
            lambda scope: build_tables_queries(scope).get_decision_table(
                table_id=table_id
            ),
        )
