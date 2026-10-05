from factors.features.combinations.use_cases import (
    CombinationsUseCases,
    ListCombinationsRequest,
)
from factors.features.generation.use_cases import (
    GenerationUseCases,
    RequestGenerationRequest,
)
from factors.features.generation.worker import run_generation_job
from factors.features.rules.use_cases import (
    CreateRuleRequest,
    ListRulesRequest,
    RulesUseCases,
)
from factors.features.tables.use_cases import AddFactorValueRequest, TablesUseCases
from factors.shared.pagination import PageRequest
from tests.helpers import DEFAULT_TEST_MAX_COMBINATIONS, build_standard_table


async def test_rules_reapply_automatically_when_generation_completes(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    browser_id, chrome_id = fixture["browser_id"], fixture["browser_values"][0]

    job = (
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
            )
        )
    ).job
    await run_generation_job(database=database, job_id=job.id, batch_size=5)

    await RulesUseCases(database).create_rule(
        CreateRuleRequest(
            table_id=table_id,
            factor_values=((browser_id, chrome_id),),
            output="Chrome path",
        )
    )

    # Add a new factor value and regenerate — the fresh combinations start
    # unreviewed with no output; the completed-generation hook should
    # replay the rule over them without any manual reapply call.
    new_os_id = (
        (
            await TablesUseCases(database).add_factor_value(
                AddFactorValueRequest(
                    table_id=table_id, factor_id=fixture["os_id"], value="ChromeOS"
                )
            )
        ).value
    ).id
    job = (
        await GenerationUseCases(database).request_generation(
            RequestGenerationRequest(
                table_id=table_id, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS
            )
        )
    ).job
    await run_generation_job(database=database, job_id=job.id, batch_size=5)

    new_rows = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(
                table_id=table_id,
                factor_values=((browser_id, chrome_id), (fixture["os_id"], new_os_id)),
                page=PageRequest(limit=100),
            )
        )
    ).page
    assert new_rows.total == 2  # the new OS value x 2 login states
    assert all(
        c.status == "possible" and c.output == "Chrome path" for c in new_rows.items
    )

    rules = (
        await RulesUseCases(database).list_rules(
            ListRulesRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert (
        rules.items[0].matched_count == 8
    )  # 4 OS values x 2 login states, post-regeneration
