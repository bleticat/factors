import pytest

from app.combinations.use_cases import (
    BulkFilterInput,
    BulkPatchInput,
    CombinationsUseCases,
)
from app.rules.ports.rule_queries import RuleValueDTO
from app.rules.use_cases import RulesUseCases
from app.shared.errors import NotFoundError, ValidationError
from app.shared.pagination import PageRequest
from app.tables.errors import (
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)
from app.tables.use_cases import TablesUseCases
from tests.helpers import (
    add_factor_with_values,
    build_standard_table,
    generate_and_wait,
)


async def test_create_rule_applies_immediately_to_matching_subset(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_out_id = fixture["login_values"][1]
    await generate_and_wait(database, table_id)

    result = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((login_id, login_out_id),),
        output="N/A when logged out",
    )
    assert result.matched_count == 9  # 3 browsers x 3 OS
    assert result.applied_at is not None

    possible = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="possible", page=PageRequest(limit=100)
    )
    assert possible.total == 9
    assert all(c.output == "N/A when logged out" for c in possible.items)


async def test_create_rule_with_empty_assignment_matches_all_rows(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    result = await RulesUseCases(database).create_rule(
        table_id=table_id, output="default"
    )
    assert result.matched_count == 18


async def test_list_rules_reflects_created_rule(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="Chrome path",
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.total == 1
    rule = page.items[0]
    assert rule.output == "Chrome path"
    assert rule.matched_count == 6  # 3 OS x 2 login states
    assert rule.factor_values == [
        RuleValueDTO(factor_id=browser_id, factor_value_id=chrome_id)
    ]


async def test_create_rule_reflects_a_given_title(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    await RulesUseCases(database).create_rule(
        table_id=table_id, output="x", title="Default output"
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.items[0].title == "Default output"


async def test_create_rule_without_title_defaults_to_none(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    await RulesUseCases(database).create_rule(table_id=table_id, output="x")

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.items[0].title is None


async def test_create_rule_normalizes_a_blank_title_to_none(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    await RulesUseCases(database).create_rule(
        table_id=table_id, output="x", title="   "
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.items[0].title is None


async def test_rules_replay_in_creation_order_on_reapply(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )

    result = await RulesUseCases(database).reapply_rules(table_id=table_id)
    assert [r.matched_count for r in result.results] == [6, 2]

    narrow_rows = await CombinationsUseCases(database).list_combinations(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        page=PageRequest(limit=100),
    )
    assert all(c.output == "narrow" for c in narrow_rows.items)

    broad_only_rows = await CombinationsUseCases(database).list_combinations(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, fixture["os_values"][1])),
        page=PageRequest(limit=100),
    )
    assert broad_only_rows.total == 2
    assert all(c.output == "broad" for c in broad_only_rows.items)


async def test_reapply_rules_on_demand_refreshes_matched_count(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_in_id = fixture["login_values"][0]
    await generate_and_wait(database, table_id)

    created = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((login_id, login_in_id),),
        output="signed in",
    )
    assert created.matched_count == 9

    # A manual bulk-patch reverts the rule's rows; reapplying it should
    # re-set them without needing a new generation.
    await CombinationsUseCases(database).bulk_patch_combinations(
        table_id=table_id,
        filter=BulkFilterInput(factor_values=((login_id, login_in_id),)),
        patch=BulkPatchInput(status="unreviewed", output=None, output_set=True),
    )
    possible = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="possible", page=PageRequest(limit=100)
    )
    assert possible.total == 0

    result = await RulesUseCases(database).reapply_rules(table_id=table_id)
    assert len(result.results) == 1
    assert result.results[0].matched_count == 9

    possible = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="possible", page=PageRequest(limit=100)
    )
    assert possible.total == 9


async def test_create_rule_rejects_empty_output(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    with pytest.raises(ValidationError):
        await RulesUseCases(database).create_rule(table_id=table_id, output="   ")


async def test_create_rule_rejects_unknown_factor(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    with pytest.raises(UnknownFactorInFilterError):
        await RulesUseCases(database).create_rule(
            table_id=table_id, factor_values=((999, 1),), output="x"
        )


async def test_create_rule_rejects_value_not_belonging_to_factor(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    os_value_id = fixture["os_values"][0]
    with pytest.raises(UnknownFactorValueInFilterError):
        await RulesUseCases(database).create_rule(
            table_id=table_id,
            factor_values=((browser_id, os_value_id),),
            output="x",
        )


async def test_create_rule_rejects_duplicate_factor_in_assignment(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    chrome_id, firefox_id = fixture["browser_values"][0], fixture["browser_values"][1]
    with pytest.raises(ValidationError):
        await RulesUseCases(database).create_rule(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (browser_id, firefox_id)),
            output="x",
        )


async def test_create_rule_allows_refining_an_existing_rule_with_a_more_specific_one(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    narrow = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )
    assert narrow.matched_count == 2


async def test_create_rule_allows_incomparable_assignments(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="browser rule",
    )
    os_rule = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((os_id, windows_id),), output="os rule"
    )
    assert os_rule.matched_count == 6


async def test_create_rule_allows_a_broader_rule_after_a_narrower_one(database):
    # Spec 009: generality is no longer enforced — a rule more general than
    # an existing one is allowed to be created; it just ends up shadowing
    # (or being shadowed by) the other, surfaced via `shadowed_count`
    # (see test_list_rules_reports_shadowed_count below) rather than rejected.
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )
    broad = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    assert broad.matched_count == 6


async def test_create_rule_allows_a_duplicate_assignment(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="first"
    )
    second = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="second"
    )
    assert second.id is not None


async def test_create_rule_allows_an_empty_assignment_after_any_rule_exists(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="specific",
    )
    default = await RulesUseCases(database).create_rule(
        table_id=table_id, output="default"
    )
    assert default.matched_count == 18


async def test_list_rules_reports_shadowed_count(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(database, table_id)

    specific = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="specific",
    )
    # Created *after* `specific` and broader — every one of `specific`'s 6
    # rows is also matched by this rule, and it wins on all of them.
    await RulesUseCases(database).create_rule(table_id=table_id, output="default")

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    specific_dto = next(r for r in page.items if r.id == specific.id)
    assert specific_dto.shadowed_count == 6  # fully shadowed: every matched row, hidden

    default_dto = next(r for r in page.items if r.output == "default")
    assert default_dto.shadowed_count == 0  # nothing comes after it


async def test_list_rules_reports_partial_shadowing(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    broad = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    # Refines `broad` on only 2 of its 6 rows.
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    broad_dto = next(r for r in page.items if r.id == broad.id)
    assert broad_dto.matched_count == 6
    assert broad_dto.shadowed_count == 2  # only the rows the narrower rule also matches


async def test_list_rules_reports_shadowing_from_the_union_of_several_later_rules(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id = fixture["os_id"]
    windows_id, mac_id = fixture["os_values"][0], fixture["os_values"][1]
    await generate_and_wait(database, table_id)

    broad = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    # Neither of these alone covers all 6 of `broad`'s rows, but together
    # they cover 4 of them (2 login states x {windows, mac}).
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="windows",
    )
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, mac_id)),
        output="mac",
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    broad_dto = next(r for r in page.items if r.id == broad.id)
    assert broad_dto.shadowed_count == 4


async def test_rule_creation_never_touches_another_table(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    browser_id, chrome_id = fixture_a["browser_id"], fixture_a["browser_values"][0]

    await RulesUseCases(database).create_rule(
        table_id=fixture_a["table_id"],
        factor_values=((browser_id, chrome_id),),
        output="a-specific",
    )
    # A table-wide default on a *different* table is unaffected by fixture_a's rule.
    default = await RulesUseCases(database).create_rule(
        table_id=fixture_b["table_id"], output="b-default"
    )
    assert default.id is not None


async def test_delete_rule_for_other_table_raises_not_found(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    rule = await RulesUseCases(database).create_rule(
        table_id=fixture_a["table_id"], output="x"
    )

    with pytest.raises(NotFoundError):
        await RulesUseCases(database).delete_rule(
            table_id=fixture_b["table_id"], rule_id=rule.id
        )


async def test_delete_rule_does_not_revert_rows_it_set(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    rule = await RulesUseCases(database).create_rule(
        table_id=table_id, output="default"
    )
    await RulesUseCases(database).delete_rule(table_id=table_id, rule_id=rule.id)

    possible = await CombinationsUseCases(database).list_combinations(
        table_id=table_id, status="possible", page=PageRequest(limit=100)
    )
    assert possible.total == 18
    assert all(c.output == "default" for c in possible.items)


async def test_deleting_a_factor_deletes_all_rules_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_in_id = fixture["login_values"][0]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((login_id, login_in_id),), output="x"
    )
    # Incomparable with the rule above (constrains a different factor, not a
    # subset or superset of it) so it doesn't trip the spec 007 "no rule may
    # be as-general-or-more-general than an existing one" check.
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="unrelated-to-login-factor",
    )

    await TablesUseCases(database).delete_factor(table_id=table_id, factor_id=login_id)

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.total == 0


async def test_deleting_a_factor_value_deletes_all_rules_for_the_table(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    await add_factor_with_values(database, table_id, "unused", ["placeholder"])
    await RulesUseCases(database).create_rule(table_id=table_id, output="x")

    await TablesUseCases(database).delete_factor_value(
        table_id=table_id,
        factor_id=browser_id,
        value_id=fixture["browser_values"][0],
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert page.total == 0


async def test_rules_never_cross_tables(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    await generate_and_wait(database, fixture_a["table_id"])
    await generate_and_wait(database, fixture_b["table_id"])

    await RulesUseCases(database).create_rule(
        table_id=fixture_a["table_id"], output="a-only"
    )

    b_rules = await RulesUseCases(database).list_rules(
        table_id=fixture_b["table_id"], page=PageRequest(limit=100)
    )
    assert b_rules.total == 0
    b_possible = await CombinationsUseCases(database).list_combinations(
        table_id=fixture_b["table_id"],
        status="possible",
        page=PageRequest(limit=100),
    )
    assert b_possible.total == 0
