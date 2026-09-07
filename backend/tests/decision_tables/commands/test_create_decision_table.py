import pytest

from app.decision_tables.commands.create_decision_table import (
    CreateDecisionTableCommand,
)
from app.decision_tables.commands.delete_decision_table import (
    DeleteDecisionTableCommand,
)
from app.decision_tables.commands.update_decision_table import (
    UpdateDecisionTableCommand,
)
from app.decision_tables.domain.errors import DecisionTableNotFoundError, EmptyNameError
from app.decision_tables.queries.get_decision_table import GetDecisionTableQuery
from tests.decision_tables.helpers import create_table


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
