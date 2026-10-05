from app.shared.pagination import PageRequest
from app.tables.use_cases import (
    AddFactorRequest,
    AddFactorValueRequest,
    ListDecisionTablesRequest,
    ListFactorsRequest,
    TablesUseCases,
)
from tests.helpers import create_table


async def test_list_decision_tables_orders_most_recently_created_first(database):
    await create_table(database, name="First")
    await create_table(database, name="Second")
    await create_table(database, name="Third")

    page = (await TablesUseCases(database).list_decision_tables()).page
    assert [t.name for t in page.items] == ["Third", "Second", "First"]
    assert page.total == 3


async def test_list_decision_tables_reports_factor_count(database):
    table_id = await create_table(database, name="Has factors")
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="Browser")
    )
    await TablesUseCases(database).add_factor(
        AddFactorRequest(table_id=table_id, name="OS")
    )
    await create_table(database, name="No factors")

    page = (
        await TablesUseCases(database).list_decision_tables(
            ListDecisionTablesRequest(page=PageRequest(limit=100))
        )
    ).page
    by_name = {t.name: t.factor_count for t in page.items}
    assert by_name["Has factors"] == 2
    assert by_name["No factors"] == 0


async def test_list_factors_returns_factors_with_nested_values(database):
    table_id = await create_table(database)
    factor = (
        await TablesUseCases(database).add_factor(
            AddFactorRequest(table_id=table_id, name="Browser")
        )
    ).factor

    await TablesUseCases(database).add_factor_value(
        AddFactorValueRequest(table_id=table_id, factor_id=factor.id, value="Chrome")
    )

    factors = (
        await TablesUseCases(database).list_factors(
            ListFactorsRequest(table_id=table_id)
        )
    ).factors
    assert len(factors) == 1
    assert factors[0].name == "Browser"
    assert [v.value for v in factors[0].values] == ["Chrome"]
