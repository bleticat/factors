from app.composition import build_tables_commands, build_tables_queries
from app.shared.execution import run_command, run_query
from app.shared.pagination import PageRequest
from tests.helpers import create_table


async def test_list_decision_tables_orders_most_recently_created_first(database):
    await create_table(database, name="First")
    await create_table(database, name="Second")
    await create_table(database, name="Third")

    page = await run_query(
        database, lambda scope: build_tables_queries(scope).list_decision_tables()
    )
    assert [t.name for t in page.items] == ["Third", "Second", "First"]
    assert page.total == 3


async def test_list_decision_tables_reports_factor_count(database):
    table_id = await create_table(database, name="Has factors")
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )
    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(table_id=table_id, name="OS"),
    )
    await create_table(database, name="No factors")

    page = await run_query(
        database,
        lambda scope: build_tables_queries(scope).list_decision_tables(
            page=PageRequest(limit=100)
        ),
    )
    by_name = {t.name: t.factor_count for t in page.items}
    assert by_name["Has factors"] == 2
    assert by_name["No factors"] == 0


async def test_list_factors_returns_factors_with_nested_values(database):
    table_id = await create_table(database)
    factor = await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor(
            table_id=table_id, name="Browser"
        ),
    )

    await run_command(
        database,
        lambda uow: build_tables_commands(uow).add_factor_value(
            table_id=table_id, factor_id=factor.id, value="Chrome"
        ),
    )

    factors = await run_query(
        database,
        lambda scope: build_tables_queries(scope).list_factors(table_id=table_id),
    )
    assert len(factors) == 1
    assert factors[0].name == "Browser"
    assert [v.value for v in factors[0].values] == ["Chrome"]
