import pytest

from factors.features.tables.use_cases import (
    AddFactorRequest,
    AddFactorValueRequest,
    DeleteFactorValueRequest,
    GetDecisionTableRequest,
    TablesUseCases,
    UpdateFactorValueRequest,
)
from factors.shared.errors import (
    InvariantViolationError,
    NotFoundError,
    ValidationError,
)
from tests.helpers import create_table


async def _make_factor(database, table_id: int, name: str = "Browser") -> int:
    factor = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name=name)
        )
    ).factor
    return factor.id


async def test_add_factor_value_appends_with_incrementing_order_index(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    first = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Chrome"
            )
        )
    ).value
    second = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Firefox"
            )
        )
    ).value
    assert first.order_index == 0
    assert second.order_index == 1


async def test_add_factor_value_rejects_duplicate_within_factor(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    await TablesUseCases(database).add_factor_value(
        AddFactorValueRequest(table_id=table_id, factor_id=factor_id, value="Chrome")
    )
    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Chrome"
            )
        )


async def test_add_factor_value_rejects_empty_value(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    with pytest.raises(ValidationError):
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(table_id=table_id, factor_id=factor_id, value="  ")
        )


async def test_update_factor_value_renames(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    value = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Chrome"
            )
        )
    ).value
    updated = (
        await TablesUseCases(database).update_factor_value(
            UpdateFactorValueRequest(
                table_id=table_id,
                factor_id=factor_id,
                value_id=value.id,
                value="Chromium",
            )
        )
    ).value
    assert updated.value == "Chromium"


async def test_delete_factor_value_leaves_remaining_values_order_index_untouched(
    database,
):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    chrome = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Chrome"
            )
        )
    ).value
    firefox = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Firefox"
            )
        )
    ).value
    safari = (
        await TablesUseCases(database).add_factor_value(
            AddFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value="Safari"
            )
        )
    ).value

    await TablesUseCases(database).delete_factor_value(
        DeleteFactorValueRequest(
            table_id=table_id, factor_id=factor_id, value_id=firefox.id
        )
    )

    table = (
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=table_id)
        )
    ).table
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
            DeleteFactorValueRequest(
                table_id=table_id, factor_id=factor_id, value_id=999
            )
        )
