"""Shared test-setup helpers. Per ADR 005, these only handle arrangement
(creating tables/factors/values, driving generation to completion) — they
must never hide the use-case call a test is actually verifying.
"""

from __future__ import annotations

from app.generation.entities import TERMINAL_STATUSES
from app.generation.service import GenerationJobRef
from app.generation.use_cases import GenerationUseCases
from app.shared.ports.database import Database
from app.tables.use_cases import TablesUseCases

_TERMINAL_STATUS_VALUES = {str(status) for status in TERMINAL_STATUSES}

# Matches the cap production wires from `settings.max_combinations`; kept
# generous here so ordinary fixture tables never trip it. Pass a smaller
# value directly to `request_generation`/`generate_and_wait` to exercise
# the cap-rejection path (see tests/generation/test_request_generation.py).
DEFAULT_TEST_MAX_COMBINATIONS = 1000


async def create_table(
    database: Database, name: str = "Test table", description: str | None = None
) -> int:
    ref = await TablesUseCases(database).create_decision_table(name, description)
    return ref.id


async def add_factor_with_values(
    database: Database, table_id: int, name: str, values: list[str]
) -> tuple[int, list[int]]:
    tables = TablesUseCases(database)
    factor = await tables.add_factor(table_id, name)
    value_ids = [
        (await tables.add_factor_value(table_id, factor.id, v)).id for v in values
    ]
    return factor.id, value_ids


async def build_standard_table(database: Database) -> dict[str, int | list[int]]:
    """3 x 3 x 2 = 18-combination table: Browser x OS x Login state."""
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
) -> GenerationJobRef:
    generation = GenerationUseCases(database)
    job = await generation.request_generation(
        table_id, max_combinations=max_combinations
    )
    result: GenerationJobRef = job
    while result.status not in _TERMINAL_STATUS_VALUES:
        result = await generation.generate_combinations_batch(job.id, batch_size)
    return result
