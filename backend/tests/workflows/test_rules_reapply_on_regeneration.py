"""Verifies spec 005's "rules re-apply automatically once generation
completes" behavior. That hook lives in the generation worker boundary
(`app.generation.worker.run_generation_job`), not in a command handler
(ADR 007's "handlers must not call the mediator"), so this must drive
generation through that boundary rather than the raw
`GenerateCombinationsBatchCommand` loop `tests/helpers.generate_and_wait`
uses.
"""

from __future__ import annotations

from app.combinations.queries import ListCombinationsQuery
from app.generation.commands import RequestGenerationCommand
from app.generation.worker import run_generation_job
from app.rules.commands import CreateRuleCommand
from app.rules.queries import ListRulesQuery
from app.shared.pagination import PageRequest
from app.tables.commands import AddFactorValueCommand
from tests.helpers import build_standard_table


async def test_rules_reapply_automatically_when_generation_completes(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    await run_generation_job(mediator=mediator, job_id=job.id, batch_size=5)

    await mediator.execute(
        CreateRuleCommand(table_id=table_id, factor_values=((browser_id, chrome_id),), output="Chrome path")
    )

    # Add a new factor value and regenerate — the fresh combinations start
    # unreviewed with no output; the completed-generation hook should
    # replay the rule over them without any manual reapply call.
    new_os_id = (
        await mediator.execute(
            AddFactorValueCommand(table_id=table_id, factor_id=fixture["os_id"], value="ChromeOS")
        )
    ).id
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    await run_generation_job(mediator=mediator, job_id=job.id, batch_size=5)

    new_rows = await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            factor_values=((browser_id, chrome_id), (fixture["os_id"], new_os_id)),
            page=PageRequest(limit=100),
        )
    )
    assert new_rows.total == 2  # the new OS value x 2 login states
    assert all(c.status == "possible" and c.output == "Chrome path" for c in new_rows.items)

    rules = await mediator.execute(ListRulesQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert rules.items[0].matched_count == 8  # 4 OS values x 2 login states, post-regeneration
