from app.generation.entities import TERMINAL_STATUSES, GenerationJob
from app.generation.use_cases import (
    GenerateCombinationsBatchRequest,
    GenerationUseCases,
    RequestGenerationRequest,
)
from app.shared.ports.database import Database
from app.tables.use_cases import (
    AddFactorRequest,
    AddFactorValueRequest,
    CreateDecisionTableRequest,
    TablesUseCases,
)

# Matches the cap production wires from `settings.max_combinations`; kept
# generous here so ordinary fixture tables never trip it. Pass a smaller
# value directly to `request_generation`/`generate_and_wait` to exercise
# the cap-rejection path (see tests/generation/test_request_generation.py).
DEFAULT_TEST_MAX_COMBINATIONS = 1000


async def create_table(
    database: Database, name: str = "Test table", description: str | None = None
) -> int:
    response = await TablesUseCases(database).create_decision_table(
        CreateDecisionTableRequest(name, description)
    )
    return response.table.id


async def add_factor_with_values(
    database: Database, table_id: int, name: str, values: list[str]
) -> tuple[int, list[int]]:
    tables = TablesUseCases(database)
    factor = (await tables.add_factor(AddFactorRequest(table_id, name))).factor
    value_ids = [
        (
            await tables.add_factor_value(AddFactorValueRequest(table_id, factor.id, v))
        ).value.id
        for v in values
    ]
    return factor.id, value_ids


async def build_standard_table(database: Database) -> dict[str, int | list[int]]:
    table_id = await create_table(database, "Login flow")
    browser_id, browser_values = await add_factor_with_values(
        database, table_id, "Browser", ["Chrome", "Firefox", "Safari"]
    )
    os_id, os_values = await add_factor_with_values(
        database, table_id, "OS", ["Windows", "Mac", "Linux"]
    )
    login_id, login_values = await add_factor_with_values(
        database, table_id, "Login state", ["in", "out"]
    )
    return {
        "table_id": table_id,
        "browser_id": browser_id,
        "browser_values": browser_values,
        "os_id": os_id,
        "os_values": os_values,
        "login_id": login_id,
        "login_values": login_values,
    }


async def generate_and_wait(
    database: Database,
    table_id: int,
    batch_size: int = 5,
    *,
    max_combinations: int = DEFAULT_TEST_MAX_COMBINATIONS,
) -> GenerationJob:
    generation = GenerationUseCases(database)
    response = await generation.request_generation(
        RequestGenerationRequest(table_id, max_combinations=max_combinations)
    )
    job = response.job
    while job.status not in TERMINAL_STATUSES:
        job = (
            await generation.generate_combinations_batch(
                GenerateCombinationsBatchRequest(job.id, batch_size)
            )
        ).job
    return job
