import pytest

from app.decision_tables.commands.create_rule import CreateRuleCommand
from app.decision_tables.commands.update_rule import UpdateRuleCommand
from app.decision_tables.domain.errors import EmptyNameError, RuleNotFoundError
from app.decision_tables.queries.list_combinations import ListCombinationsQuery
from app.decision_tables.queries.list_rules import ListRulesQuery
from app.shared.pagination import PageRequest
from tests.decision_tables.helpers import build_standard_table, generate_and_wait


async def test_update_rule_output_repatches_matching_rows(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(mediator, table_id)

    created = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="old")
    )
    result = await mediator.execute(
        UpdateRuleCommand(table_id=table_id, rule_id=created.id, output="new")
    )
    assert result.matched_count == 6

    rows = await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id, factor_values=((browser_id, chrome_id),), page=PageRequest(limit=100)
        )
    )
    assert all(c.output == "new" for c in rows.items)


async def test_update_rule_title_only_does_not_change_matched_count_or_applied_at(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    created = await mediator.execute(CreateRuleCommand(table_id=table_id, output="x"))
    before = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))

    await mediator.execute(
        UpdateRuleCommand(table_id=table_id, rule_id=created.id, title="A label", title_set=True)
    )

    after = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert after.items[0].title == "A label"
    assert after.items[0].matched_count == before.items[0].matched_count
    assert after.items[0].applied_at == before.items[0].applied_at


async def test_update_rule_narrows_assignment_and_leaves_stale_rows_untouched(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(mediator, table_id)

    created = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="chrome")
    )
    result = await mediator.execute(
        UpdateRuleCommand(
            table_id=table_id,
            rule_id=created.id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            factor_values_set=True,
        )
    )
    assert result.matched_count == 2

    # Rows the rule used to match but no longer does keep the stale output
    # (spec 008's "still no revert").
    stale = await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, fixture["os_values"][1])),
            page=PageRequest(limit=100),
        )
    )
    assert all(c.output == "chrome" for c in stale.items)


async def test_update_rule_allows_widening_past_an_earlier_rule(mediator):
    # Spec 009: no longer rejected — `narrow` simply ends up shadowed by the
    # freshly-widened `broad` (see test_rules.py's shadowed_count coverage).
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(mediator, table_id)

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad")
    )
    narrow = await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        )
    )

    result = await mediator.execute(
        UpdateRuleCommand(
            table_id=table_id,
            rule_id=narrow.id,
            factor_values=((browser_id, chrome_id),),
            factor_values_set=True,
        )
    )
    assert result.matched_count == 6


async def test_update_rule_allows_duplicating_another_rules_assignment(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="a")
    )
    other = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((os_id, windows_id),), output="b")
    )

    result = await mediator.execute(
        UpdateRuleCommand(
            table_id=table_id,
            rule_id=other.id,
            factor_values=((browser_id, chrome_id),),
            factor_values_set=True,
        )
    )
    assert result.id == other.id


async def test_update_rule_rejects_blank_output(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    created = await mediator.execute(CreateRuleCommand(table_id=table_id, output="x"))

    with pytest.raises(EmptyNameError):
        await mediator.execute(UpdateRuleCommand(table_id=table_id, rule_id=created.id, output="   "))


async def test_update_rule_for_other_table_raises_not_found(mediator):
    fixture_a = await build_standard_table(mediator)
    fixture_b = await build_standard_table(mediator)
    rule = await mediator.execute(CreateRuleCommand(table_id=fixture_a["table_id"], output="x"))

    with pytest.raises(RuleNotFoundError):
        await mediator.execute(
            UpdateRuleCommand(table_id=fixture_b["table_id"], rule_id=rule.id, output="y")
        )
