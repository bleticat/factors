import pytest

from app.decision_tables.commands.add_factor import AddFactorCommand
from app.decision_tables.commands.delete_factor import DeleteFactorCommand
from app.decision_tables.commands.update_factor import UpdateFactorCommand
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorNameError,
    EmptyNameError,
    FactorNotFoundError,
)
from app.decision_tables.queries.get_decision_table import GetDecisionTableQuery
from tests.decision_tables.helpers import create_table


async def test_add_factor_appends_with_incrementing_order_index(mediator):
    table_id = await create_table(mediator)
    first = await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    second = await mediator.execute(AddFactorCommand(table_id=table_id, name="OS"))
    assert first.order_index == 0
    assert second.order_index == 1

    table = await mediator.execute(GetDecisionTableQuery(table_id=table_id))
    assert [f.name for f in table.factors] == ["Browser", "OS"]


async def test_add_factor_rejects_empty_name(mediator):
    table_id = await create_table(mediator)
    with pytest.raises(EmptyNameError):
        await mediator.execute(AddFactorCommand(table_id=table_id, name="  "))


async def test_add_factor_rejects_duplicate_name_within_table(mediator):
    table_id = await create_table(mediator)
    await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    with pytest.raises(DuplicateFactorNameError):
        await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))


async def test_add_factor_allows_same_name_in_different_table(mediator):
    table_a = await create_table(mediator, name="A")
    table_b = await create_table(mediator, name="B")
    await mediator.execute(AddFactorCommand(table_id=table_a, name="Browser"))
    await mediator.execute(AddFactorCommand(table_id=table_b, name="Browser"))  # must not raise


async def test_add_factor_against_missing_table_raises(mediator):
    with pytest.raises(DecisionTableNotFoundError):
        await mediator.execute(AddFactorCommand(table_id=999, name="Browser"))


async def test_update_factor_renames_without_disturbing_order_index(mediator):
    table_id = await create_table(mediator)
    factor = await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    updated = await mediator.execute(
        UpdateFactorCommand(table_id=table_id, factor_id=factor.id, name="Web Browser")
    )
    assert updated.name == "Web Browser"
    assert updated.order_index == factor.order_index


async def test_update_factor_against_factor_in_different_table_raises_not_found(mediator):
    table_a = await create_table(mediator, name="A")
    table_b = await create_table(mediator, name="B")
    factor = await mediator.execute(AddFactorCommand(table_id=table_a, name="Browser"))
    with pytest.raises(FactorNotFoundError):
        await mediator.execute(UpdateFactorCommand(table_id=table_b, factor_id=factor.id, name="X"))


async def test_delete_factor_removes_it_and_its_values(mediator):
    table_id = await create_table(mediator)
    factor = await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=factor.id))
    table = await mediator.execute(GetDecisionTableQuery(table_id=table_id))
    assert table.factors == []


async def test_delete_factor_does_not_affect_other_factors(mediator):
    table_id = await create_table(mediator)
    browser = await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    await mediator.execute(AddFactorCommand(table_id=table_id, name="OS"))
    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=browser.id))

    table = await mediator.execute(GetDecisionTableQuery(table_id=table_id))
    assert [f.name for f in table.factors] == ["OS"]
