import pytest

from app.combinations.use_cases import (
    BulkFilterInput,
    BulkPatchInput,
    CombinationsUseCases,
)
from app.shared.errors import ValidationError
from app.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_bulk_patch_filtered_by_one_factor_value_matches_only_that_subset(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_out_id = fixture["login_values"][1]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=table_id,
        filter=BulkFilterInput(factor_values=((login_id, login_out_id),)),
        patch=BulkPatchInput(
            status="impossible",
            impossible_reason="N/A when logged out",
            impossible_reason_set=True,
        ),
    )
    assert result.matched_count == 9  # 3 browsers x 3 OS
    assert result.updated_count == 9

    impossible = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="impossible", page=PageRequest(limit=100)
    )
    assert impossible.total == 9

    unreviewed = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="unreviewed", page=PageRequest(limit=100)
    )
    assert unreviewed.total == 9  # the "in" half untouched


async def test_bulk_patch_with_two_and_ed_constraints_matches_intersection(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=table_id,
        filter=BulkFilterInput(
            factor_values=((browser_id, chrome_id), (os_id, windows_id))
        ),
        patch=BulkPatchInput(status="possible"),
    )
    assert result.matched_count == 2  # Chrome+Windows, both login states


async def test_bulk_patch_rejects_unknown_factor_in_filter(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    with pytest.raises(ValidationError):
        await CombinationsUseCases(database).bulk_patch_combinations(
            table_id=table_id,
            filter=BulkFilterInput(factor_values=((999, 1),)),
            patch=BulkPatchInput(status="possible"),
        )


async def test_bulk_patch_rejects_value_not_belonging_to_factor(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    os_value_id = fixture["os_values"][0]  # belongs to OS, not Browser
    await generate_and_wait(database, table_id)

    with pytest.raises(ValidationError):
        await CombinationsUseCases(database).bulk_patch_combinations(
            table_id=table_id,
            filter=BulkFilterInput(factor_values=((browser_id, os_value_id),)),
            patch=BulkPatchInput(status="possible"),
        )


async def test_bulk_patch_with_no_matches_returns_zero_without_error(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=table_id,
        filter=BulkFilterInput(status="possible"),  # nothing is 'possible' yet
        patch=BulkPatchInput(status="impossible"),
    )
    assert result.matched_count == 0
    assert result.updated_count == 0


async def test_bulk_patch_with_empty_filter_matches_every_row_in_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    result = await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=table_id, patch=BulkPatchInput(status="possible")
    )
    assert result.matched_count == 18
    assert result.updated_count == 18


async def test_bulk_patch_never_touches_another_tables_combinations(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    await generate_and_wait(database, fixture_a["table_id"])
    await generate_and_wait(database, fixture_b["table_id"])

    await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=fixture_a["table_id"], patch=BulkPatchInput(status="possible")
    )

    b_unreviewed = await CombinationsUseCases(database).list_combinations(
        table_id=fixture_b["table_id"],
        status="unreviewed",
        page=PageRequest(limit=100),
    )
    assert b_unreviewed.total == 18  # table B untouched
