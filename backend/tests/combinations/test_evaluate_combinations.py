import pytest

from app.combinations.use_cases import CombinationsUseCases
from app.shared.errors import DuplicateFactorInAssignmentError
from app.shared.pagination import PageRequest
from app.tables.errors import (
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)
from tests.helpers import (
    build_standard_table,
    create_table,
    generate_and_wait,
)


async def test_full_assignment_returns_exactly_one_match_with_its_current_state(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    login_id, login_in_id = fixture["login_id"], fixture["login_values"][0]
    await generate_and_wait(database, table_id)

    # Mark the target row so we can confirm evaluate reflects live state.
    page = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, page=PageRequest(limit=100)
    )
    target = next(
        c
        for c in page.items
        if {(v.factor_id, v.factor_value_id) for v in c.values}
        == {(browser_id, chrome_id), (os_id, windows_id), (login_id, login_in_id)}
    )
    await CombinationsUseCases(database).patch_combination(
        table_id=table_id,
        combination_id=target.id,
        status="possible",
        output="ok",
        output_set=True,
    )

    result = await CombinationsUseCases(database).evaluate_combinations(
        table_id=table_id,
        assignment=(
            (browser_id, chrome_id),
            (os_id, windows_id),
            (login_id, login_in_id),
        ),
    )
    assert result.kind == "single"
    assert result.combination is not None
    assert result.combination.id == target.id
    assert result.combination.status == "possible"
    assert result.combination.output == "ok"


async def test_partial_assignment_returns_consistent_subset(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id, login_out_id = fixture["login_id"], fixture["login_values"][1]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).evaluate_combinations(
        table_id=table_id,
        assignment=((login_id, login_out_id),),
        page=PageRequest(limit=100),
    )
    assert result.kind == "list"
    assert result.page is not None
    assert result.page.total == 9


async def test_empty_assignment_returns_every_combination(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).evaluate_combinations(
        table_id=table_id, assignment=(), page=PageRequest(limit=100)
    )
    assert result.kind == "list"
    assert result.page.total == 18


async def test_full_assignment_against_ungenerated_table_returns_none(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    login_id, login_in_id = fixture["login_id"], fixture["login_values"][0]
    # Note: generation never run.

    result = await CombinationsUseCases(database).evaluate_combinations(
        table_id=table_id,
        assignment=(
            (browser_id, chrome_id),
            (os_id, windows_id),
            (login_id, login_in_id),
        ),
    )
    assert result.kind == "single"
    assert result.combination is None


async def test_single_factor_table_full_assignment_is_one_pair(database):
    table_id = await create_table(database, name="Single factor")
    from tests.helpers import add_factor_with_values

    factor_id, value_ids = await add_factor_with_values(
        database, table_id, "Browser", ["Chrome", "Firefox"]
    )
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).evaluate_combinations(
        table_id=table_id, assignment=((factor_id, value_ids[0]),)
    )
    assert result.kind == "single"
    assert result.combination is not None


async def test_assignment_pair_with_unknown_factor_is_rejected(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    with pytest.raises(UnknownFactorInFilterError):
        await CombinationsUseCases(database).evaluate_combinations(
            table_id=table_id, assignment=((999, 1),)
        )


async def test_assignment_pair_with_value_not_belonging_to_factor_is_rejected(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    os_value_id = fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    with pytest.raises(UnknownFactorValueInFilterError):
        await CombinationsUseCases(database).evaluate_combinations(
            table_id=table_id, assignment=((browser_id, os_value_id),)
        )


async def test_assignment_with_duplicate_factor_is_rejected(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    chrome_id, firefox_id = fixture["browser_values"][0], fixture["browser_values"][1]
    await generate_and_wait(database, table_id)

    with pytest.raises(DuplicateFactorInAssignmentError):
        await CombinationsUseCases(database).evaluate_combinations(
            table_id=table_id,
            assignment=((browser_id, chrome_id), (browser_id, firefox_id)),
        )
