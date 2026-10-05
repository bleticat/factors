import pytest

from app.shared.errors import NotFoundError, ValidationError
from app.tables.use_cases import (
    CreateDecisionTableRequest,
    DeleteDecisionTableRequest,
    GetDecisionTableRequest,
    TablesUseCases,
    UpdateDecisionTableRequest,
)
from tests.helpers import create_table


async def test_create_decision_table_succeeds(database):
    ref = (
        await TablesUseCases(database).create_decision_table(
            CreateDecisionTableRequest(name="Login flow", description="desc")
        )
    ).table
    assert ref.name == "Login flow"
    assert ref.description == "desc"

    table = (
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=ref.id)
        )
    ).table
    assert table.name == "Login flow"
    assert table.factors == []


async def test_create_decision_table_rejects_empty_name(database):
    with pytest.raises(ValidationError):
        await TablesUseCases(database).create_decision_table(
            CreateDecisionTableRequest(name="   ")
        )


async def test_update_decision_table_renames_and_redescribes(database):
    table_id = await create_table(database, name="Old", description="old desc")
    updated = (
        await TablesUseCases(database).update_decision_table(
            UpdateDecisionTableRequest(
                table_id=table_id,
                name="New",
                description="new desc",
                description_set=True,
            )
        )
    ).table
    assert updated.name == "New"
    assert updated.description == "new desc"


async def test_update_decision_table_against_missing_table_raises(database):
    with pytest.raises(NotFoundError):
        await TablesUseCases(database).update_decision_table(
            UpdateDecisionTableRequest(table_id=999, name="X")
        )


async def test_delete_decision_table_then_get_raises_not_found(database):
    table_id = await create_table(database)
    await TablesUseCases(database).delete_decision_table(
        DeleteDecisionTableRequest(table_id=table_id)
    )
    with pytest.raises(NotFoundError):
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=table_id)
        )
