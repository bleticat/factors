import pytest

from app.shared.errors import NotFoundError, ValidationError
from app.tables.errors import DuplicateFactorValueError
from app.tables.use_cases import TablesUseCases
from tests.helpers import create_table


async def _make_factor(database, table_id: int, name: str = "Browser") -> int:
    factor = await TablesUseCases(database).add_factor(table_id=table_id, name=name)
    return factor.id


async def test_add_factor_value_appends_with_incrementing_order_index(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    first = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Chrome"
    )
    second = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Firefox"
    )
    assert first.order_index == 0
    assert second.order_index == 1


async def test_add_factor_value_rejects_duplicate_within_factor(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Chrome"
    )
    with pytest.raises(DuplicateFactorValueError):
        await TablesUseCases(database).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Chrome"
        )


async def test_add_factor_value_rejects_empty_value(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    with pytest.raises(ValidationError):
        await TablesUseCases(database).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="  "
        )


async def test_update_factor_value_renames(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    value = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Chrome"
    )
    updated = await TablesUseCases(database).update_factor_value(
        table_id=table_id, factor_id=factor_id, value_id=value.id, value="Chromium"
    )
    assert updated.value == "Chromium"


async def test_delete_factor_value_leaves_remaining_values_order_index_untouched(
    database,
):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    chrome = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Chrome"
    )
    firefox = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Firefox"
    )
    safari = await TablesUseCases(database).add_factor_value(
        table_id=table_id, factor_id=factor_id, value="Safari"
    )

    await TablesUseCases(database).delete_factor_value(
        table_id=table_id, factor_id=factor_id, value_id=firefox.id
    )

    table = await TablesUseCases(database).get_decision_table(table_id=table_id)
    remaining = table.factors[0].values
    assert [(v.value, v.order_index) for v in remaining] == [
        (chrome.value, chrome.order_index),
        (safari.value, safari.order_index),
    ]


async def test_delete_factor_value_against_missing_value_raises(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    with pytest.raises(NotFoundError):
        await TablesUseCases(database).delete_factor_value(
            table_id=table_id, factor_id=factor_id, value_id=999
        )
