"""The full plan-level verification flow, as a single workflow test:
create table -> add factors/values -> generate -> review/bulk-refine ->
evaluate (full and partial). Composes commands and queries from all four
feature specs, so it belongs here rather than under commands/ or queries/.
"""

from app.combinations.commands import (
    BulkFilterInput,
    BulkPatchCombinationsCommand,
    BulkPatchInput,
    PatchCombinationCommand,
)
from app.combinations.queries import EvaluateCombinationsQuery, ListCombinationsQuery
from app.shared.pagination import PageRequest
from app.tables.queries import GetDecisionTableQuery
from tests.helpers import build_standard_table, generate_and_wait


async def test_full_decision_table_lifecycle(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]
    os_id, windows_id = fixture["os_id"], fixture["os_values"][0]
    login_id, login_in_id, login_out_id = (
        fixture["login_id"],
        fixture["login_values"][0],
        fixture["login_values"][1],
    )

    table = await mediator.execute(GetDecisionTableQuery(table_id=table_id))
    assert len(table.factors) == 3

    job = await generate_and_wait(mediator, table_id, batch_size=5)
    assert job.status == "completed"
    assert job.created_count == 18

    page = await mediator.execute(ListCombinationsQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 18
    target = next(
        c
        for c in page.items
        if {(v.factor_id, v.factor_value_id) for v in c.values}
        == {(browser_id, chrome_id), (os_id, windows_id), (login_id, login_in_id)}
    )
    await mediator.execute(
        PatchCombinationCommand(
            table_id=table_id,
            combination_id=target.id,
            status="possible",
            output="user reaches dashboard",
            output_set=True,
        )
    )

    bulk_result = await mediator.execute(
        BulkPatchCombinationsCommand(
            table_id=table_id,
            filter=BulkFilterInput(factor_values=((login_id, login_out_id),)),
            patch=BulkPatchInput(
                status="impossible", impossible_reason="N/A when logged out", impossible_reason_set=True
            ),
        )
    )
    assert bulk_result.updated_count == 9

    full = await mediator.execute(
        EvaluateCombinationsQuery(
            table_id=table_id,
            assignment=((browser_id, chrome_id), (os_id, windows_id), (login_id, login_in_id)),
        )
    )
    assert full.kind == "single"
    assert full.combination.status == "possible"
    assert full.combination.output == "user reaches dashboard"

    partial = await mediator.execute(
        EvaluateCombinationsQuery(
            table_id=table_id, assignment=((login_id, login_out_id),), page=PageRequest(limit=100)
        )
    )
    assert partial.kind == "list"
    assert partial.page.total == 9
    assert all(c.status == "impossible" for c in partial.page.items)
