from app.decision_tables.commands.generate_combinations_batch import (
    GenerateCombinationsBatchCommand,
)
from app.decision_tables.queries.list_combinations import ListCombinationsQuery
from app.shared.pagination import PageRequest
from tests.decision_tables.helpers import build_standard_table, generate_and_wait


async def test_batching_to_completion_produces_all_combinations_once_each(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]

    result = await generate_and_wait(mediator, table_id, batch_size=5)
    assert result.status == "completed"
    assert result.created_count == 18
    assert result.total_combinations == 18

    page = await mediator.execute(ListCombinationsQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 18

    signatures = set()
    for combo in page.items:
        assert len(combo.values) == 3  # one pick per factor
        signature = tuple(sorted((v.factor_id, v.factor_value_id) for v in combo.values))
        signatures.add(signature)
    assert len(signatures) == 18  # every tuple is unique


async def test_batch_command_is_idempotent_after_completion(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(mediator, table_id, batch_size=5)
    assert completed.status == "completed"

    # Calling again must be a no-op, not create more rows.
    again = await mediator.execute(GenerateCombinationsBatchCommand(job_id=completed.id, batch_size=5))
    assert again.status == "completed"
    assert again.created_count == 18

    page = await mediator.execute(ListCombinationsQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 18


async def test_regenerating_replaces_previous_combinations(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    first = await generate_and_wait(mediator, table_id, batch_size=5)
    assert first.status == "completed"

    second = await generate_and_wait(mediator, table_id, batch_size=5)
    assert second.id != first.id
    assert second.status == "completed"
    assert second.created_count == 18

    page = await mediator.execute(ListCombinationsQuery(table_id=table_id, page=PageRequest(limit=100)))
    assert page.total == 18  # not 36 — old combinations were deleted, not accumulated
