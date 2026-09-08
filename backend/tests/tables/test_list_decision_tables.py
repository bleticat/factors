from app.shared.pagination import PageRequest
from app.tables.commands import AddFactorCommand
from app.tables.queries import ListDecisionTablesQuery, ListFactorsQuery
from tests.helpers import create_table


async def test_list_decision_tables_orders_most_recently_created_first(mediator):
    await create_table(mediator, name="First")
    await create_table(mediator, name="Second")
    await create_table(mediator, name="Third")

    page = await mediator.execute(ListDecisionTablesQuery())
    assert [t.name for t in page.items] == ["Third", "Second", "First"]
    assert page.total == 3


async def test_list_decision_tables_reports_factor_count(mediator):
    table_id = await create_table(mediator, name="Has factors")
    await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    await mediator.execute(AddFactorCommand(table_id=table_id, name="OS"))
    await create_table(mediator, name="No factors")

    page = await mediator.execute(ListDecisionTablesQuery(page=PageRequest(limit=100)))
    by_name = {t.name: t.factor_count for t in page.items}
    assert by_name["Has factors"] == 2
    assert by_name["No factors"] == 0


async def test_list_factors_returns_factors_with_nested_values(mediator):
    table_id = await create_table(mediator)
    factor = await mediator.execute(AddFactorCommand(table_id=table_id, name="Browser"))
    from app.tables.commands import AddFactorValueCommand

    await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor.id, value="Chrome"))

    factors = await mediator.execute(ListFactorsQuery(table_id=table_id))
    assert len(factors) == 1
    assert factors[0].name == "Browser"
    assert [v.value for v in factors[0].values] == ["Chrome"]
