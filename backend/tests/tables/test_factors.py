import pytest

from factors.features.tables.use_cases import (
    AddFactorRequest,
    DeleteFactorRequest,
    GetDecisionTableRequest,
    TablesUseCases,
    UpdateFactorRequest,
)
from factors.shared.errors import (
    InvariantViolationError,
    NotFoundError,
    ValidationError,
)
from tests.helpers import create_table


async def test_add_factor_appends_with_incrementing_order_index(database):
    table_id = await create_table(database)
    first = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )
    ).factor
    second = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="OS")
        )
    ).factor
    assert first.order_index == 0
    assert second.order_index == 1

    table = (
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=table_id)
        )
    ).table
    assert [f.name for f in table.factors] == ["Browser", "OS"]


async def test_add_factor_rejects_empty_name(database):
    table_id = await create_table(database)
    with pytest.raises(ValidationError):
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="  ")
        )


async def test_add_factor_rejects_duplicate_name_within_table(database):
    table_id = await create_table(database)
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="Browser")
    )
    with pytest.raises(InvariantViolationError):
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )


async def test_add_factor_allows_same_name_in_different_table(database):
    table_a = await create_table(database, name="A")
    table_b = await create_table(database, name="B")
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_a, name="Browser")
    )
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_b, name="Browser")
    )  # must not raise


async def test_add_factor_against_missing_table_raises(database):
    with pytest.raises(NotFoundError):
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=999, name="Browser")
        )


async def test_update_factor_renames_without_disturbing_order_index(database):
    table_id = await create_table(database)
    factor = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )
    ).factor
    updated = (
        await TablesUseCases(database).update_factor(
            UpdateFactorRequest(
                table_id=table_id, factor_id=factor.id, name="Web Browser"
            )
        )
    ).factor
    assert updated.name == "Web Browser"
    assert updated.order_index == factor.order_index


async def test_update_factor_against_factor_in_different_table_raises_not_found(
    database,
):
    table_a = await create_table(database, name="A")
    table_b = await create_table(database, name="B")
    factor = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_a, name="Browser")
        )
    ).factor
    with pytest.raises(NotFoundError):
        await TablesUseCases(database).update_factor(
            UpdateFactorRequest(table_id=table_b, factor_id=factor.id, name="X")
        )


async def test_delete_factor_removes_it_and_its_values(database):
    table_id = await create_table(database)
    factor = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )
    ).factor
    await TablesUseCases(database).delete_factor(
        DeleteFactorRequest(table_id=table_id, factor_id=factor.id)
    )
    table = (
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=table_id)
        )
    ).table
    assert table.factors == []


async def test_delete_factor_does_not_affect_other_factors(database):
    table_id = await create_table(database)
    browser = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )
    ).factor
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="OS")
    )
    await TablesUseCases(database).delete_factor(
        DeleteFactorRequest(table_id=table_id, factor_id=browser.id)
    )

    table = (
        await TablesUseCases(database).get_decision_table(
            GetDecisionTableRequest(table_id=table_id)
        )
    ).table
    assert [f.name for f in table.factors] == ["OS"]
