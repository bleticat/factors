from app.combinations.use_cases import CombinationsUseCases, ListCombinationsRequest
from app.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_list_combinations_filters_by_status(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    all_page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert all_page.total == 18

    unreviewed = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id, status="unreviewed", page=PageRequest(limit=100)
            )
        )
    ).page
    assert unreviewed.total == 18

    possible = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id, status="possible", page=PageRequest(limit=100)
            )
        )
    ).page
    assert possible.total == 0


async def test_list_combinations_paginates_across_a_page_boundary(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    first_page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id, page=PageRequest(limit=10, offset=0)
            )
        )
    ).page
    second_page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id, page=PageRequest(limit=10, offset=10)
            )
        )
    ).page
    assert len(first_page.items) == 10
    assert len(second_page.items) == 8
    assert first_page.total == second_page.total == 18
    first_ids = {c.id for c in first_page.items}
    second_ids = {c.id for c in second_page.items}
    assert first_ids.isdisjoint(second_ids)
