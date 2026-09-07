"""Shared test-setup helpers. Per ADR 005, these only handle arrangement
(creating tables/factors/values, driving generation to completion) — they
must never hide the command or query request a test is actually verifying.
"""

from __future__ import annotations

from app.decision_tables.commands.add_factor import AddFactorCommand
from app.decision_tables.commands.add_factor_value import AddFactorValueCommand
from app.decision_tables.commands.create_decision_table import (
    CreateDecisionTableCommand,
)
from app.decision_tables.commands.generate_combinations_batch import (
    GenerateCombinationsBatchCommand,
)
from app.decision_tables.commands.request_generation import RequestGenerationCommand
from app.decision_tables.commands.results import GenerationJobRef
from app.decision_tables.domain.generation_job import TERMINAL_STATUSES
from app.shared.mediator.mediator import Mediator

_TERMINAL_STATUS_VALUES = {str(status) for status in TERMINAL_STATUSES}


async def create_table(mediator: Mediator, name: str = "Test table", description: str | None = None) -> int:
    ref = await mediator.execute(CreateDecisionTableCommand(name=name, description=description))
    return ref.id


async def add_factor_with_values(
    mediator: Mediator, table_id: int, name: str, values: list[str]
) -> tuple[int, list[int]]:
    factor = await mediator.execute(AddFactorCommand(table_id=table_id, name=name))
    value_ids = [
        (await mediator.execute(AddFactorValueCommand(table_id=table_id, factor_id=factor.id, value=v))).id
        for v in values
    ]
    return factor.id, value_ids


async def build_standard_table(mediator: Mediator) -> dict[str, int | list[int]]:
    """3 x 3 x 2 = 18-combination table: Browser x OS x Login state."""
    table_id = await create_table(mediator, "Login flow")
    browser_id, browser_values = await add_factor_with_values(
        mediator, table_id, "Browser", ["Chrome", "Firefox", "Safari"]
    )
    os_id, os_values = await add_factor_with_values(mediator, table_id, "OS", ["Windows", "Mac", "Linux"])
    login_id, login_values = await add_factor_with_values(mediator, table_id, "Login state", ["in", "out"])
    return {
        "table_id": table_id,
        "browser_id": browser_id,
        "browser_values": browser_values,
        "os_id": os_id,
        "os_values": os_values,
        "login_id": login_id,
        "login_values": login_values,
    }


async def generate_and_wait(mediator: Mediator, table_id: int, batch_size: int = 5) -> GenerationJobRef:
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    result: GenerationJobRef = job
    while result.status not in _TERMINAL_STATUS_VALUES:
        result = await mediator.execute(
            GenerateCombinationsBatchCommand(job_id=job.id, batch_size=batch_size)
        )
    return result
