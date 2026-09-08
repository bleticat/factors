import pytest

from app.shared.errors import EmptyNameError
from app.tables.commands import (
    CreateDecisionTableCommand,
    DeleteDecisionTableCommand,
    UpdateDecisionTableCommand,
)
from app.tables.errors import DecisionTableNotFoundError
from app.tables.queries import GetDecisionTableQuery
from tests.helpers import create_table


async def test_create_decision_table_succeeds(mediator):
    ref = await mediator.execute(CreateDecisionTableCommand(name="Login flow", description="desc"))
    assert ref.name == "Login flow"
    assert ref.description == "desc"

    table = await mediator.execute(GetDecisionTableQuery(table_id=ref.id))
    assert table.name == "Login flow"
    assert table.factors == []


async def test_create_decision_table_rejects_empty_name(mediator):
    with pytest.raises(EmptyNameError):
        await mediator.execute(CreateDecisionTableCommand(name="   "))


async def test_update_decision_table_renames_and_redescribes(mediator):
    table_id = await create_table(mediator, name="Old", description="old desc")
    updated = await mediator.execute(
        UpdateDecisionTableCommand(
            table_id=table_id, name="New", description="new desc", description_set=True
        )
    )
    assert updated.name == "New"
    assert updated.description == "new desc"


async def test_update_decision_table_against_missing_table_raises(mediator):
    with pytest.raises(DecisionTableNotFoundError):
        await mediator.execute(UpdateDecisionTableCommand(table_id=999, name="X"))


async def test_delete_decision_table_then_get_raises_not_found(mediator):
    table_id = await create_table(mediator)
    await mediator.execute(DeleteDecisionTableCommand(table_id=table_id))
    with pytest.raises(DecisionTableNotFoundError):
        await mediator.execute(GetDecisionTableQuery(table_id=table_id))
