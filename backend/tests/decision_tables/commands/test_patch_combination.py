import pytest

from app.decision_tables.commands.patch_combination import PatchCombinationCommand
from app.decision_tables.domain.errors import (
    CombinationNotFoundError,
    InvalidCombinationStatusError,
)
from tests.decision_tables.helpers import build_standard_table, generate_and_wait


async def _first_combination_id(mediator, table_id: int) -> int:
    from app.decision_tables.queries.list_combinations import ListCombinationsQuery

    page = await mediator.execute(ListCombinationsQuery(table_id=table_id))
    return page.items[0].id


async def test_patch_combination_sets_status_and_output(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)
    combination_id = await _first_combination_id(mediator, table_id)

    result = await mediator.execute(
        PatchCombinationCommand(
            table_id=table_id,
            combination_id=combination_id,
            status="possible",
            output="user reaches dashboard",
            output_set=True,
        )
    )
    assert result.status == "possible"
    assert result.output == "user reaches dashboard"


async def test_patch_combination_sets_impossible_reason(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)
    combination_id = await _first_combination_id(mediator, table_id)

    result = await mediator.execute(
        PatchCombinationCommand(
            table_id=table_id,
            combination_id=combination_id,
            status="impossible",
            impossible_reason="not applicable",
            impossible_reason_set=True,
        )
    )
    assert result.status == "impossible"
    assert result.impossible_reason == "not applicable"


async def test_patch_combination_rejects_invalid_status(mediator):
    fixture = await build_standard_table(mediator)
    table_id = fixture["table_id"]
    await generate_and_wait(mediator, table_id)
    combination_id = await _first_combination_id(mediator, table_id)

    with pytest.raises(InvalidCombinationStatusError):
        await mediator.execute(
            PatchCombinationCommand(table_id=table_id, combination_id=combination_id, status="bogus")
        )


async def test_patch_combination_from_a_different_table_raises_not_found(mediator):
    fixture_a = await build_standard_table(mediator)
    fixture_b = await build_standard_table(mediator)
    await generate_and_wait(mediator, fixture_a["table_id"])
    await generate_and_wait(mediator, fixture_b["table_id"])
    combination_from_a = await _first_combination_id(mediator, fixture_a["table_id"])

    with pytest.raises(CombinationNotFoundError):
        await mediator.execute(
            PatchCombinationCommand(
                table_id=fixture_b["table_id"], combination_id=combination_from_a, status="possible"
            )
        )
