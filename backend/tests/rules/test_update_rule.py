import pytest

from factors.features.combinations.use_cases import (
    CombinationsUseCases,
    ListCombinationsRequest,
)
from factors.features.rules.use_cases import (
    CreateRuleRequest,
    ListRulesRequest,
    RulesUseCases,
    UpdateRuleRequest,
)
from factors.shared.errors import NotFoundError, ValidationError
from factors.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_update_rule_output_repatches_matching_rows(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(database, table_id)

    created = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id),),
                output="old",
            )
        )
    ).rule
    result = (
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(table_id=table_id, rule_id=created.id, output="new")
        )
    ).rule
    assert result.matched_count == 6

    rows = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id),),
                page=PageRequest(limit=100),
            )
        )
    ).page
    assert all(c.output == "new" for c in rows.items)


async def test_update_rule_title_only_does_not_change_matched_count_or_applied_at(
    database,
):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    created = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=table_id, output="x")
        )
    ).rule
    before = (
        await RulesUseCases(database).list_rules(
            ListRulesRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page

    await RulesUseCases(database).update_rule(
        UpdateRuleRequest(
            table_id=table_id, rule_id=created.id, title="A label", title_set=True
        )
    )

    after = (
        await RulesUseCases(database).list_rules(
            ListRulesRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert after.items[0].title == "A label"
    assert after.items[0].matched_count == before.items[0].matched_count
    assert after.items[0].applied_at == before.items[0].applied_at


async def test_update_rule_narrows_assignment_and_leaves_stale_rows_untouched(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    created = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id),),
                output="chrome",
            )
        )
    ).rule
    result = (
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(
                table_id=table_id,
                rule_id=created.id,
                factor_values=((browser_id, chrome_id), (os_id, windows_id)),
                factor_values_set=True,
            )
        )
    ).rule
    assert result.matched_count == 2

    # Rows the rule used to match but no longer does keep the stale output
    # (spec 008's "still no revert").
    stale = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id,
                factor_values=(
                    (browser_id, chrome_id),
                    (os_id, fixture["os_values"][1]),
                ),
                page=PageRequest(limit=100),
            )
        )
    ).page
    assert all(c.output == "chrome" for c in stale.items)


async def test_update_rule_allows_widening_past_an_earlier_rule(database):
    # Spec 009: no longer rejected — `narrow` simply ends up shadowed by the
    # freshly-widened `broad` (see test_rules.py's shadowed_count coverage).
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await RulesUseCases(database).create_rule(
        CreateRuleRequest(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
        )
    )
    narrow = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (os_id, windows_id)),
                output="narrow",
            )
        )
    ).rule

    result = (
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(
                table_id=table_id,
                rule_id=narrow.id,
                factor_values=((browser_id, chrome_id),),
                factor_values_set=True,
            )
        )
    ).rule
    assert result.matched_count == 6


async def test_update_rule_allows_duplicating_another_rules_assignment(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    await RulesUseCases(database).create_rule(
        CreateRuleRequest(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="a"
        )
    )
    other = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id, factor_values=((os_id, windows_id),), output="b"
            )
        )
    ).rule

    result = (
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(
                table_id=table_id,
                rule_id=other.id,
                factor_values=((browser_id, chrome_id),),
                factor_values_set=True,
            )
        )
    ).rule
    assert result.id == other.id


async def test_update_rule_rejects_blank_output(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    created = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=table_id, output="x")
        )
    ).rule

    with pytest.raises(ValidationError):
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(table_id=table_id, rule_id=created.id, output="   ")
        )


async def test_update_rule_for_other_table_raises_not_found(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    rule = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=fixture_a["table_id"], output="x")
        )
    ).rule

    with pytest.raises(NotFoundError):
        await RulesUseCases(database).update_rule(
            UpdateRuleRequest(
                table_id=fixture_b["table_id"], rule_id=rule.id, output="y"
            )
        )
