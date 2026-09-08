import pytest

from app.composition import build_tables_commands, build_tables_queries
from app.shared.errors import EmptyNameError
from app.shared.execution import run_command, run_query
from app.tables.errors import DuplicateFactorValueError, FactorValueNotFoundError
from tests.helpers import create_table


async def _make_factor(database, table_id: int, name: str = "Browser") -> int:
    factor = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(table_id=table_id, name=name),
    )
    return factor.id


async def test_add_factor_value_appends_with_incrementing_order_index(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    first = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Chrome"
        ),
    )
    second = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Firefox"
        ),
    )
    assert first.order_index == 0
    assert second.order_index == 1


async def test_add_factor_value_rejects_duplicate_within_factor(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Chrome"
        ),
    )
    with pytest.raises(DuplicateFactorValueError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor_value(
                table_id=table_id, factor_id=factor_id, value="Chrome"
            ),
        )


async def test_add_factor_value_rejects_empty_value(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    with pytest.raises(EmptyNameError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).add_factor_value(
                table_id=table_id, factor_id=factor_id, value="  "
            ),
        )


async def test_update_factor_value_renames(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    value = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Chrome"
        ),
    )
    updated = await run_command(
        database,
        lambda uow: build_tables_commands(uow).update_factor_value(
            table_id=table_id, factor_id=factor_id, value_id=value.id, value="Chromium"
        ),
    )
    assert updated.value == "Chromium"


async def test_delete_factor_value_leaves_remaining_values_order_index_untouched(
    database,
):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    chrome = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Chrome"
        ),
    )
    firefox = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Firefox"
        ),
    )
    safari = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor_id, value="Safari"
        ),
    )

    await run_command(
        database,
        lambda uow: build_tables_commands(uow).delete_factor_value(
            table_id=table_id, factor_id=factor_id, value_id=firefox.id
        ),
    )

    table = await run_query(
        database,
        lambda scope: build_tables_queries(scope).get_decision_table(table_id=table_id),
    )
    remaining = table.factors[0].values
    assert [(v.value, v.order_index) for v in remaining] == [
        (chrome.value, chrome.order_index),
        (safari.value, safari.order_index),
    ]


async def test_delete_factor_value_against_missing_value_raises(database):
    table_id = await create_table(database)
    factor_id = await _make_factor(database, table_id)
    with pytest.raises(FactorValueNotFoundError):
        await run_command(
            database,
            lambda uow: build_tables_commands(uow).delete_factor_value(
                table_id=table_id, factor_id=factor_id, value_id=999
            ),
        )
