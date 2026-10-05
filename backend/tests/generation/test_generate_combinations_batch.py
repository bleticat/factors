from factors.features.combinations.use_cases import (
    CombinationsUseCases,
    ListCombinationsRequest,
)
from factors.features.generation.use_cases import (
    GenerateCombinationsBatchRequest,
    GenerationUseCases,
)
from factors.shared.pagination import PageRequest
from tests.helpers import build_standard_table, generate_and_wait


async def test_batching_to_completion_produces_all_combinations_once_each(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]

    result = await generate_and_wait(database, table_id, batch_size=5)
    assert result.status == "completed"
    assert result.created_count == 18
    assert result.total_combinations == 18

    page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert page.total == 18

    signatures = set()
    for combo in page.items:
        assert len(combo.values) == 3  # one pick per factor
        signature = tuple(
            sorted((v.factor_id, v.factor_value_id) for v in combo.values)
        )
        signatures.add(signature)
    assert len(signatures) == 18  # every tuple is unique


async def test_batch_command_is_idempotent_after_completion(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    completed = await generate_and_wait(database, table_id, batch_size=5)
    assert completed.status == "completed"

    # Calling again must be a no-op, not create more rows.
    again = (
        await GenerationUseCases(database).generate_combinations_batch(
            GenerateCombinationsBatchRequest(job_id=completed.id, batch_size=5)
        )
    ).job
    assert again.status == "completed"
    assert again.created_count == 18

    page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert page.total == 18


async def test_regenerating_replaces_previous_combinations(database):
    fixture = await build_standard_table(database)
    table_id = fixture["table_id"]
    first = await generate_and_wait(database, table_id, batch_size=5)
    assert first.status == "completed"

    second = await generate_and_wait(database, table_id, batch_size=5)
    assert second.id != first.id
    assert second.status == "completed"
    assert second.created_count == 18

    page = (
        await CombinationsUseCases(database).list_combinations(
            ListCombinationsRequest(table_id=table_id, page=PageRequest(limit=100))
        )
    ).page
    assert page.total == 18  # not 36 — old combinations were deleted, not accumulated
