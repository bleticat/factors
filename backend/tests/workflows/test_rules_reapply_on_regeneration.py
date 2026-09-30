"""Verifies spec 005's "rules re-apply automatically once generation
completes" behavior. That hook lives in the generation worker boundary
(`app.application.generation.worker.run_generation_job`), which drives a job across
multiple batches/transactions and reapplies rules once it completes — a
single `generate_combinations_batch` call can't do that on its own, so this
must drive generation through the real worker loop rather than the raw
batch-call loop `tests/helpers.generate_and_wait` uses.
"""

from __future__ import annotations

from app.application.combinations.use_cases import CombinationsUseCases
from app.application.generation.use_cases import GenerationUseCases
from app.application.generation.worker import run_generation_job
from app.application.pagination import PageRequest
from app.application.rules.use_cases import RulesUseCases
from app.application.tables.use_cases import TablesUseCases
from tests.helpers import DEFAULT_TEST_MAX_COMBINATIONS, build_standard_table


async def test_rules_reapply_automatically_when_generation_completes(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    job = await GenerationUseCases(database).request_generation(
        table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
    )
    await run_generation_job(database=database, job_id=job.id, batch_size=5)

    await RulesUseCases(database).create_rule(
        table_id=table_id,
        factor_values=((browser_id, chrome_id),),
        output="Chrome path",
    )

    # Add a new factor value and regenerate — the fresh combinations start
    # unreviewed with no output; the completed-generation hook should
    # replay the rule over them without any manual reapply call.
    new_os_id = (
        await TablesUseCases(database).add_factor_value(
            table_id=table_id, factor_id=fixture["os_id"], value="ChromeOS"
        )
    ).id
    job = await GenerationUseCases(database).request_generation(
        table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
    )
    await run_generation_job(database=database, job_id=job.id, batch_size=5)

    new_rows = await CombinationsUseCases(database).list_combinations(
        table_id=table_id,
        factor_values=((browser_id, chrome_id), (fixture["os_id"], new_os_id)),
        page=PageRequest(limit=100),
    )
    assert new_rows.total == 2  # the new OS value x 2 login states
    assert all(
        c.status == "possible" and c.output == "Chrome path" for c in new_rows.items
    )

    rules = await RulesUseCases(database).list_rules(
        table_id=table_id, page=PageRequest(limit=100)
    )
    assert (
        rules.items[0].matched_count == 8
    )  # 4 OS values x 2 login states, post-regeneration
