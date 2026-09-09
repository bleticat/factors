import pytest

from app.combinations.use_cases import CombinationsUseCases
from app.rules.errors import InvalidRuleOrderError
from app.rules.use_cases import RulesUseCases
from app.shared.pagination import PageRequest
from app.tables.errors import DecisionTableNotFoundError
from tests.helpers import build_standard_table, generate_and_wait


async def test_reorder_persists_new_order_and_reflects_in_list_rules(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    # Two rules incomparable with each other, so either order is valid on
    # its own; a third refines the first.
    a = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="a"
    )
    b = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((os_id, windows_id),), output="b"
    )

    await RulesUseCases(database).reorder_rules(
        table_id=table_id, ordered_rule_ids=(b.id, a.id)
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert [r.id for r in page.items] == [b.id, a.id]
    assert [r.order_index for r in page.items] == [0, 1]


async def test_reorder_reapplies_all_rules_in_the_new_order(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    broad = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    narrow = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )
    # As created, narrow (later) wins on the overlap.
    overlap = await CombinationsUseCases(database).list_combinations(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        page=PageRequest(limit=100),
    )
    assert all(c.output == "narrow" for c in overlap.items)

    # Reordering is only valid one way here (broad must stay first, since
    # narrow refines it) — reasserting the same order still triggers a
    # fresh reapply.
    result = await RulesUseCases(database).reorder_rules(
        table_id=table_id, ordered_rule_ids=(broad.id, narrow.id)
    )
    assert [r.matched_count for r in result.results] == [6, 2]


async def test_reorder_rejects_a_list_missing_a_rule(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    a = await RulesUseCases(database).create_rule(table_id=table_id, output="a")
    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((fixture["browser_id"], fixture["browser_values"][0]),),
        output="b",
    )

    with pytest.raises(InvalidRuleOrderError):
        await RulesUseCases(database).reorder_rules(
            table_id=table_id, ordered_rule_ids=(a.id,)
        )


async def test_reorder_rejects_a_foreign_rule_id(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    a = await RulesUseCases(database).create_rule(
        table_id=fixture_a["table_id"], output="a"
    )
    foreign = await RulesUseCases(database).create_rule(
        table_id=fixture_b["table_id"], output="b"
    )

    with pytest.raises(InvalidRuleOrderError):
        await RulesUseCases(database).reorder_rules(
            table_id=fixture_a["table_id"], ordered_rule_ids=(foreign.id, a.id)
        )


async def test_reorder_rejects_a_duplicated_id(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    a = await RulesUseCases(database).create_rule(table_id=table_id, output="a")

    with pytest.raises(InvalidRuleOrderError):
        await RulesUseCases(database).reorder_rules(
            table_id=table_id, ordered_rule_ids=(a.id, a.id)
        )


async def test_reorder_allows_an_order_that_shadows_a_rule(database):
    # Spec 009: no generality check on reorder either — `narrow` is simply
    # shadowed by `broad` in this order (surfaced via `shadowed_count`),
    # not rejected.
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    broad = await RulesUseCases(database).create_rule(
        table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
    )
    narrow = await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (os_id, windows_id)),
        output="narrow",
    )

    await RulesUseCases(database).reorder_rules(
        table_id=table_id, ordered_rule_ids=(narrow.id, broad.id)
    )

    page = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert [r.id for r in page.items] == [narrow.id, broad.id]


async def test_reorder_for_missing_table_raises_not_found(database):
    with pytest.raises(DecisionTableNotFoundError):
        await RulesUseCases(database).reorder_rules(table_id=999, ordered_rule_ids=())
