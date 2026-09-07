import pytest

from app.decision_tables.commands.bulk_patch_combinations import (
    BulkFilterInput,
    BulkPatchCombinationsCommand,
    BulkPatchInput,
)
from app.decision_tables.commands.create_rule import CreateRuleCommand
from app.decision_tables.commands.delete_factor import DeleteFactorCommand
from app.decision_tables.commands.delete_factor_value import DeleteFactorValueCommand
from app.decision_tables.commands.delete_rule import DeleteRuleCommand
from app.decision_tables.commands.reapply_rules import ReapplyRulesCommand
from app.decision_tables.domain.errors import (
    DuplicateFactorInAssignmentError,
    EmptyNameError,
    RuleNotFoundError,
    RuleTooGeneralError,
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)
from app.decision_tables.ports.rule_queries import RuleValueDTO
from app.decision_tables.queries.list_combinations import ListCombinationsQuery
from app.decision_tables.queries.list_rules import ListRulesQuery
from app.shared.pagination import PageRequest
from tests.decision_tables.helpers import (
    add_factor_with_values,
    build_standard_table,
    generate_and_wait,
)


async def test_create_rule_applies_immediately_to_matching_subset(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_out_id = fixture["login_values"][1]
    await generate_and_wait(mediator, table_id)

    result = await mediator.execute(
        CreateRuleCommand(
            table_id=table_id, factor_values=((login_id, login_out_id),), output="N/A when logged out"
        )
    )
    assert result.matched_count == 9  # 3 browsers x 3 OS
    assert result.applied_at is not None

    possible = await mediator.execute(
        ListCombinationsQuery(table_id=table_id, status="possible", page=PageRequest(limit=100))
    )
    assert possible.total == 9
    assert all(c.output == "N/A when logged out" for c in possible.items)


async def test_create_rule_with_empty_assignment_matches_all_rows(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    result = await mediator.execute(CreateRuleCommand(table_id=table_id, output="default"))
    assert result.matched_count == 18


async def test_list_rules_reflects_created_rule(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(mediator, table_id)

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="Chrome path")
    )

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 1
    rule = page.items[0]
    assert rule.output == "Chrome path"
    assert rule.matched_count == 6  # 3 OS x 2 login states
    assert rule.factor_values == [RuleValueDTO(factor_id=browser_id, factor_value_id=chrome_id)]


async def test_create_rule_reflects_a_given_title(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]

    await mediator.execute(CreateRuleCommand(table_id=table_id, output="x", title="Default output"))

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.items[0].title == "Default output"


async def test_create_rule_without_title_defaults_to_none(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]

    await mediator.execute(CreateRuleCommand(table_id=table_id, output="x"))

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.items[0].title is None


async def test_create_rule_normalizes_a_blank_title_to_none(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]

    await mediator.execute(CreateRuleCommand(table_id=table_id, output="x", title="   "))

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.items[0].title is None


async def test_rules_replay_in_creation_order_on_reapply(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(mediator, table_id)

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad")
    )
    await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        )
    )

    result = await mediator.execute(ReapplyRulesCommand(table_id=table_id))
    assert [r.matched_count for r in result.results] == [6, 2]

    narrow_rows = await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            page=PageRequest(limit=100),
        )
    )
    assert all(c.output == "narrow" for c in narrow_rows.items)

    broad_only_rows = await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, fixture["os_values"][1])),
            page=PageRequest(limit=100),
        )
    )
    assert broad_only_rows.total == 2
    assert all(c.output == "broad" for c in broad_only_rows.items)


async def test_reapply_rules_on_demand_refreshes_matched_count(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_in_id = fixture["login_values"][0]
    await generate_and_wait(mediator, table_id)

    created = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((login_id, login_in_id),), output="signed in")
    )
    assert created.matched_count == 9

    # A manual bulk-patch reverts the rule's rows; reapplying it should
    # re-set them without needing a new generation.
    await mediator.execute(
        BulkPatchCombinationsCommand(
            table_id=table_id,
            filter=BulkFilterInput(factor_values=((login_id, login_in_id),)),
            patch=BulkPatchInput(status="unreviewed", output=None, output_set=True),
        )
    )
    possible = await mediator.execute(
        ListCombinationsQuery(table_id=table_id, status="possible", page=PageRequest(limit=100))
    )
    assert possible.total == 0

    result = await mediator.execute(ReapplyRulesCommand(table_id=table_id))
    assert len(result.results) == 1
    assert result.results[0].matched_count == 9

    possible = await mediator.execute(
        ListCombinationsQuery(table_id=table_id, status="possible", page=PageRequest(limit=100))
    )
    assert possible.total == 9


async def test_create_rule_rejects_empty_output(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    with pytest.raises(EmptyNameError):
        await mediator.execute(CreateRuleCommand(table_id=table_id, output="   "))


async def test_create_rule_rejects_unknown_factor(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    with pytest.raises(UnknownFactorInFilterError):
        await mediator.execute(
            CreateRuleCommand(table_id=table_id, factor_values=((999, 1),), output="x")
        )


async def test_create_rule_rejects_value_not_belonging_to_factor(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    os_value_id = fixture["os_values"][0]
    with pytest.raises(UnknownFactorValueInFilterError):
        await mediator.execute(
            CreateRuleCommand(
                table_id=table_id, factor_values=((browser_id, os_value_id),), output="x"
            )
        )


async def test_create_rule_rejects_duplicate_factor_in_assignment(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    chrome_id, firefox_id = fixture["browser_values"][0], fixture["browser_values"][1]
    with pytest.raises(DuplicateFactorInAssignmentError):
        await mediator.execute(
            CreateRuleCommand(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (browser_id, firefox_id)),
                output="x",
            )
        )


async def test_create_rule_allows_refining_an_existing_rule_with_a_more_specific_one(mediator):
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
    assert narrow.matched_count == 2


async def test_create_rule_allows_incomparable_assignments(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(mediator, table_id)

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="browser rule")
    )
    os_rule = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((os_id, windows_id),), output="os rule")
    )
    assert os_rule.matched_count == 6


async def test_create_rule_rejects_a_broader_rule_after_a_narrower_one(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(mediator, table_id)

    narrow = await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        )
    )
    with pytest.raises(RuleTooGeneralError) as exc_info:
        await mediator.execute(
            CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad")
        )
    assert exc_info.value.conflicting_rule_id == narrow.id


async def test_create_rule_rejects_a_duplicate_assignment(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="first")
    )
    with pytest.raises(RuleTooGeneralError):
        await mediator.execute(
            CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="second")
        )


async def test_create_rule_rejects_an_empty_assignment_after_any_rule_exists(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="specific")
    )
    with pytest.raises(RuleTooGeneralError):
        await mediator.execute(CreateRuleCommand(table_id=table_id, output="default"))


async def test_create_rule_generality_conflict_is_scoped_to_its_own_table(mediator):
    fixture_a = await build_standard_table(mediator)
    fixture_b = await build_standard_table(mediator)
    browser_id, chrome_id = fixture_a["browser_id"], fixture_a["browser_values"][0]

    await mediator.execute(
        CreateRuleCommand(
            table_id=fixture_a["table_id"], factor_values=((browser_id, chrome_id),), output="a-specific"
        )
    )
    # A table-wide default on a *different* table is unaffected by fixture_a's rule.
    default = await mediator.execute(CreateRuleCommand(table_id=fixture_b["table_id"], output="b-default"))
    assert default.id is not None


async def test_rejected_rule_creation_does_not_persist_or_apply_anything(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(mediator, table_id)

    narrow = await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="narrow")
    )
    with pytest.raises(RuleTooGeneralError):
        await mediator.execute(CreateRuleCommand(table_id=table_id, output="default"))

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 1
    assert page.items[0].id == narrow.id
    assert page.items[0].matched_count == 6  # unaffected by the rejected attempt


async def test_delete_rule_for_other_table_raises_not_found(mediator):
    fixture_a = await build_standard_table(mediator)
    fixture_b = await build_standard_table(mediator)
    rule = await mediator.execute(CreateRuleCommand(table_id=fixture_a["table_id"], output="x"))

    with pytest.raises(RuleNotFoundError):
        await mediator.execute(DeleteRuleCommand(table_id=fixture_b["table_id"], rule_id=rule.id))


async def test_delete_rule_does_not_revert_rows_it_set(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)

    rule = await mediator.execute(CreateRuleCommand(table_id=table_id, output="default"))
    await mediator.execute(DeleteRuleCommand(table_id=table_id, rule_id=rule.id))

    possible = await mediator.execute(
        ListCombinationsQuery(table_id=table_id, status="possible", page=PageRequest(limit=100))
    )
    assert possible.total == 18
    assert all(c.output == "default" for c in possible.items)


async def test_deleting_a_factor_deletes_all_rules_for_the_table(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    login_id = fixture["login_id"]
    login_in_id = fixture["login_values"][0]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((login_id, login_in_id),), output="x")
    )
    # Incomparable with the rule above (constrains a different factor, not a
    # subset or superset of it) so it doesn't trip the spec 007 "no rule may
    # be as-general-or-more-general than an existing one" check.
    await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=((browser_id, chrome_id),),
            output="unrelated-to-login-factor",
        )
    )

    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=login_id))

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 0


async def test_deleting_a_factor_value_deletes_all_rules_for_the_table(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id = fixture["browser_id"]
    await add_factor_with_values(mediator, table_id, "unused", ["placeholder"])
    await mediator.execute(CreateRuleCommand(table_id=table_id, output="x"))

    await mediator.execute(
        DeleteFactorValueCommand(
            table_id=table_id, factor_id=browser_id, value_id=fixture["browser_values"][0]
        )
    )

    page = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 0


async def test_rules_never_cross_tables(mediator):
    fixture_a = await build_standard_table(mediator)
    fixture_b = await build_standard_table(mediator)
    await generate_and_wait(mediator, fixture_a["table_id"])
    await generate_and_wait(mediator, fixture_b["table_id"])

    await mediator.execute(CreateRuleCommand(table_id=fixture_a["table_id"], output="a-only"))

    b_rules = await mediator.execute(
        ListRulesQuery(table_id=fixture_b["table_id"], page=PageRequest(limit=100))
    )
    assert b_rules.total == 0
    b_possible = await mediator.execute(
        ListCombinationsQuery(table_id=fixture_b["table_id"], status="possible", page=PageRequest(limit=100))
    )
    assert b_possible.total == 0
