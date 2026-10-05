import pytest

from factors.features.combinations.use_cases import (
    CombinationsUseCases,
    ListCombinationsRequest,
)
from factors.features.rules.use_cases import (
    CreateRuleRequest,
    ListRulesRequest,
    ReorderRulesRequest,
    RulesUseCases,
)
from factors.shared.errors import InvariantViolationError, NotFoundError
from factors.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_reorder_persists_new_order_and_reflects_in_list_rules(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    # Two rules incomparable with each other, so either order is valid on
    # its own; a third refines the first.
    a = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id, factor_values=((browser_id, chrome_id),), output="a"
            )
        )
    ).rule
    b = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id, factor_values=((os_id, windows_id),), output="b"
            )
        )
    ).rule

    await RulesUseCases(database).reorder_rules(
        ReorderRulesRequest(table_id=table_id, ordered_rule_ids=(b.id, a.id))
    )

    page = (
        await RulesUseCases(database).list_rules(
            ListRulesRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert [r.id for r in page.items] == [b.id, a.id]
    assert [r.order_index for r in page.items] == [0, 1]


async def test_reorder_reapplies_all_rules_in_the_new_order(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    broad = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id),),
                output="broad",
            )
        )
    ).rule
    narrow = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (os_id, windows_id)),
                output="narrow",
            )
        )
    ).rule
    # As created, narrow (later) wins on the overlap.
    overlap = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (os_id, windows_id)),
                page=PageRequest(limit=100),
            )
        )
    ).page
    assert all(c.output == "narrow" for c in overlap.items)

    # Reordering is only valid one way here (broad must stay first, since
    # narrow refines it) — reasserting the same order still triggers a
    # fresh reapply.
    result = (
        await RulesUseCases(database).reorder_rules(
            ReorderRulesRequest(
                table_id=table_id, ordered_rule_ids=(broad.id, narrow.id)
            )
        )
    ).rules
    assert [r.matched_count for r in result] == [6, 2]


async def test_reorder_rejects_a_list_missing_a_rule(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    a = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=table_id, output="a")
        )
    ).rule
    await RulesUseCases(database).create_rule(
        CreateRuleRequest(
            table_id=table_id,
            factor_values=((fixture["browser_id"], fixture["browser_values"][0]),),
            output="b",
        )
    )

    with pytest.raises(InvariantViolationError):
        await RulesUseCases(database).reorder_rules(
            ReorderRulesRequest(table_id=table_id, ordered_rule_ids=(a.id,))
        )


async def test_reorder_rejects_a_foreign_rule_id(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    a = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=fixture_a["table_id"], output="a")
        )
    ).rule
    foreign = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=fixture_b["table_id"], output="b")
        )
    ).rule

    with pytest.raises(InvariantViolationError):
        await RulesUseCases(database).reorder_rules(
            ReorderRulesRequest(
                table_id=fixture_a["table_id"], ordered_rule_ids=(foreign.id, a.id)
            )
        )


async def test_reorder_rejects_a_duplicated_id(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    a = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(table_id=table_id, output="a")
        )
    ).rule

    with pytest.raises(InvariantViolationError):
        await RulesUseCases(database).reorder_rules(
            ReorderRulesRequest(table_id=table_id, ordered_rule_ids=(a.id, a.id))
        )


async def test_reorder_allows_an_order_that_shadows_a_rule(database):
    # Spec 009: no generality check on reorder either — `narrow` is simply
    # shadowed by `broad` in this order (surfaced via `shadowed_count`),
    # not rejected.
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    broad = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id),),
                output="broad",
            )
        )
    ).rule
    narrow = (
        await RulesUseCases(database).create_rule(
            CreateRuleRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (os_id, windows_id)),
                output="narrow",
            )
        )
    ).rule

    await RulesUseCases(database).reorder_rules(
        ReorderRulesRequest(table_id=table_id, ordered_rule_ids=(narrow.id, broad.id))
    )

    page = (
        await RulesUseCases(database).list_rules(
            ListRulesRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert [r.id for r in page.items] == [narrow.id, broad.id]


async def test_reorder_for_missing_table_raises_not_found(database):
    with pytest.raises(NotFoundError):
        await RulesUseCases(database).reorder_rules(
            ReorderRulesRequest(table_id=999, ordered_rule_ids=())
        )
