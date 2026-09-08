import pytest

from app.shared.errors import EmptyNameError
from app.tables.commands import (
    AddFactorCommand,
    AddFactorValueCommand,
    DeleteFactorValueCommand,
    UpdateFactorValueCommand,
)
from app.tables.errors import DuplicateFactorValueError, FactorValueNotFoundError
from app.tables.queries import GetDecisionTableQuery
from tests.helpers import create_table


async def _make_factor(mediator, table_id: int, name: str = "Browser") -> int:
    factor = await mediator.execute(AddFactorCommand(table_id=table_id, name=name))
    return factor.id


async def test_add_factor_value_appends_with_incrementing_order_index(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    first = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Chrome"))
    second = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Firefox"))
    assert first.order_index == 0
    assert second.order_index == 1


async def test_add_factor_value_rejects_duplicate_within_factor(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Chrome"))
    with pytest.raises(DuplicateFactorValueError):
        await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Chrome"))


async def test_add_factor_value_rejects_empty_value(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    with pytest.raises(EmptyNameError):
        await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="  "))


async def test_update_factor_value_renames(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    value = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Chrome"))
    updated = await mediator.execute(
        UpdateFactorValueCommand(table_id=table_id, factor_id=factor_id, value_id=value.id, value="Chromium")
    )
    assert updated.value == "Chromium"


async def test_delete_factor_value_leaves_remaining_values_order_index_untouched(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    chrome = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Chrome"))
    firefox = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Firefox"))
    safari = await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value="Safari"))

    await mediator.execute(DeleteFactorValueCommand(table_id=table_id, factor_id=factor_id, value_id=firefox.id))

    table = await mediator.execute(GetDecisionTableQuery(table_id=table_id))
    remaining = table.factors[0].values
    assert [(v.value, v.order_index) for v in remaining] == [
        (chrome.value, chrome.order_index),
        (safari.value, safari.order_index),
    ]


async def test_delete_factor_value_against_missing_value_raises(mediator):
    table_id = await create_table(mediator)
    factor_id = await _make_factor(mediator, table_id)
    with pytest.raises(FactorValueNotFoundError):
        await mediator.execute(DeleteFactorValueCommand(table_id=table_id, factor_id=factor_id, value_id=999))
