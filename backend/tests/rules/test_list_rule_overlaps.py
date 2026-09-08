from app.composition import build_rules_commands, build_rules_queries
from app.shared.execution import run_command, run_query
from app.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_overlap_returns_only_rows_matched_by_both_rules(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    broad = await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
        ),
    )
    narrow = await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        ),
    )

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 2  # Chrome x Windows x {in, out}
    for item in page.items:
        rule_ids = [r.id for r in item.matching_rules]
        assert rule_ids == [
            broad.id,
            narrow.id,
        ]  # ordered by apply order; narrow (last) is the winner
        outputs = {r.output for r in item.matching_rules}
        assert outputs == {"broad", "narrow"}


async def test_overlap_winner_follows_apply_order_after_a_reorder(database):
    # Regression: `matching_rules` must be ordered by each rule's current
    # apply position (order_index), not by rule id — otherwise the winner
    # shown here would silently disagree with what a reapply actually sets.
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    broad = await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
        ),
    )
    narrow = await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        ),
    )
    # Reorder so `broad` (the lower id) now applies *after* `narrow`.
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).reorder_rules(
            table_id=table_id, ordered_rule_ids=(narrow.id, broad.id)
        ),
    )

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 2
    for item in page.items:
        rule_ids = [r.id for r in item.matching_rules]
        assert rule_ids == [
            narrow.id,
            broad.id,
        ]  # broad now applies last, so it's the winner


async def test_overlap_excludes_rows_only_matched_by_a_disjoint_rule(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id, firefox_id = (
        fixture["browser_id"],
        fixture["browser_values"][0],
        fixture["browser_values"][1],
    )
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    await generate_and_wait(database, table_id)

    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="broad"
        ),
    )
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (os_id, windows_id)),
            output="narrow",
        ),
    )
    # Disjoint from the other two: a different browser entirely.
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id,
            factor_values=((browser_id, firefox_id),),
            output="disjoint",
        ),
    )

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 2
    for item in page.items:
        assert {r.output for r in item.matching_rules} == {"broad", "narrow"}


async def test_overlap_with_default_rule_only_flags_the_narrow_rules_rows(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    await generate_and_wait(database, table_id)

    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, output="default"
        ),
    )  # matches all 18
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="chrome"
        ),
    )

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 6  # only the Chrome rows satisfy both rules
    for item in page.items:
        assert {r.output for r in item.matching_rules} == {"default", "chrome"}


async def test_overlap_paginates_across_a_page_boundary(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    login_id, login_in_id = fixture["login_id"], fixture["login_values"][0]
    await generate_and_wait(database, table_id)

    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, output="default"
        ),
    )  # matches all 18
    # Refines the default rule (login has only 2 values, so this is the
    # broadest possible non-empty refinement on this table): 9 rows.
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id,
            factor_values=((login_id, login_in_id),),
            output="signed in",
        ),
    )

    first_page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=5, offset=0)
        ),
    )
    second_page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=5, offset=5)
        ),
    )
    assert first_page.total == second_page.total == 9
    assert len(first_page.items) == 5
    assert len(second_page.items) == 4
    first_ids = {item.combination.id for item in first_page.items}
    second_ids = {item.combination.id for item in second_page.items}
    assert first_ids.isdisjoint(second_ids)


async def test_overlap_empty_with_fewer_than_two_rules(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    await generate_and_wait(database, table_id)

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 0

    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, output="only one"
        ),
    )
    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 0


async def test_overlap_empty_when_never_generated(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]

    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((browser_id, chrome_id),), output="a"
        ),
    )
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=table_id, factor_values=((os_id, windows_id),), output="b"
        ),
    )

    page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=table_id, page=PageRequest(limit=100)
        ),
    )
    assert page.total == 0


async def test_overlap_never_crosses_tables(database):
    fixture_a = await build_standard_table(database)
    fixture_b = await build_standard_table(database)
    await generate_and_wait(database, fixture_a["table_id"])
    await generate_and_wait(database, fixture_b["table_id"])

    browser_id, chrome_id = fixture_a["browser_id"], fixture_a["browser_values"][0]
    os_id, windows_id = fixture_a["os_id"], fixture_a["os_values"][0]
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=fixture_a["table_id"],
            factor_values=((browser_id, chrome_id),),
            output="a1",
        ),
    )
    await run_command(
        database,
        lambda uow: build_rules_commands(uow).create_rule(
            table_id=fixture_a["table_id"],
            factor_values=((os_id, windows_id),),
            output="a2",
        ),
    )

    b_page = await run_query(
        database,
        lambda scope: build_rules_queries(scope).list_rule_overlaps(
            table_id=fixture_b["table_id"], page=PageRequest(limit=100)
        ),
    )
    assert b_page.total == 0
