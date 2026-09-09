import pytest

from app.shared.errors import EmptyNameError
from app.tables.errors import DecisionTableNotFoundError
from app.tables.use_cases import TablesUseCases
from tests.helpers import create_table


async def test_create_decision_table_succeeds(database):
    ref = await TablesUseCases(database).create_decision_table(
        name="Login flow", description="desc"
    )
    assert ref.name == "Login flow"
    assert ref.description == "desc"

    table = await TablesUseCases(database).get_decision_table(table_id=ref.id)
    assert table.name == "Login flow"
    assert table.factors == []


async def test_create_decision_table_rejects_empty_name(database):
    with pytest.raises(EmptyNameError):
        await TablesUseCases(database).create_decision_table(name="   ")


async def test_update_decision_table_renames_and_redescribes(database):
    table_id = await create_table(database, name="Old", description="old desc")
    updated = await TablesUseCases(database).update_decision_table(
        table_id=table_id, name="New", description="new desc", description_set=True
    )
    assert updated.name == "New"
    assert updated.description == "new desc"


async def test_update_decision_table_against_missing_table_raises(database):
    with pytest.raises(DecisionTableNotFoundError):
        await TablesUseCases(database).update_decision_table(table_id=999, name="X")


async def test_delete_decision_table_then_get_raises_not_found(database):
    table_id = await create_table(database)
    await TablesUseCases(database).delete_decision_table(table_id=table_id)
    with pytest.raises(DecisionTableNotFoundError):
        await TablesUseCases(database).get_decision_table(table_id=table_id)
