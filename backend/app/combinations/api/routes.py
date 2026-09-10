"""Thin HTTP boundary: parse input, call the module's use cases, serialize
the result."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.combinations.api import schemas
from app.combinations.use_cases import (
    BulkFilterInput,
    BulkPatchInput,
    CombinationsUseCases,
)
from app.shared.api import get_database
from app.shared.pagination import PageRequest
from app.shared.ports.database import Database

router = APIRouter()


def get_combinations_use_cases(
    database: Database = Depends(get_database),
) -> CombinationsUseCases:
    return CombinationsUseCases(database)


@router.get("/{table_id}/combinations")
async def list_combinations(
    table_id: int,
    status: str | None = None,
    fv: list[str] = Query(default_factory=list),
    limit: int = 50,
    offset: int = 0,
    use_cases: CombinationsUseCases = Depends(get_combinations_use_cases),
):
    """`fv` is a repeatable `factor_id:factor_value_id` pair, e.g.
    `?fv=3:9&fv=5:14` — the same AND-ed filter shape bulk-patch uses."""
    return await use_cases.list_combinations(
        table_id=table_id,
        status=status,
        factor_values=tuple(_parse_factor_value_pair(pair) for pair in fv),
        page=PageRequest(limit=limit, offset=offset),
    )


def _parse_factor_value_pair(pair: str) -> tuple[int, int]:
    factor_id_str, _, value_id_str = pair.partition(":")
    return int(factor_id_str), int(value_id_str)


@router.patch("/{table_id}/combinations/{combination_id}")
async def patch_combination(
    table_id: int,
    combination_id: int,
    body: schemas.PatchCombinationRequest,
    use_cases: CombinationsUseCases = Depends(get_combinations_use_cases),
):
    fields = body.model_fields_set
    return await use_cases.patch_combination(
        table_id=table_id,
        combination_id=combination_id,
        status=body.status,
        output=body.output,
        output_set="output" in fields,
        impossible_reason=body.impossible_reason,
        impossible_reason_set="impossible_reason" in fields,
    )


@router.post("/{table_id}/combinations/bulk-patch")
async def bulk_patch_combinations(
    table_id: int,
    body: schemas.BulkPatchCombinationsRequest,
    use_cases: CombinationsUseCases = Depends(get_combinations_use_cases),
):
    patch_fields = body.patch.model_fields_set
    return await use_cases.bulk_patch_combinations(
        table_id=table_id,
        filter=BulkFilterInput(
            status=body.filter.status,
            factor_values=tuple(body.filter.factor_values),
        ),
        patch=BulkPatchInput(
            status=body.patch.status,
            output=body.patch.output,
            output_set="output" in patch_fields,
            impossible_reason=body.patch.impossible_reason,
            impossible_reason_set="impossible_reason" in patch_fields,
        ),
    )


@router.post("/{table_id}/evaluate")
async def evaluate(
    table_id: int,
    body: schemas.EvaluateRequest,
    use_cases: CombinationsUseCases = Depends(get_combinations_use_cases),
):
    return await use_cases.evaluate_combinations(
        table_id=table_id,
        assignment=tuple(body.assignment),
        page=PageRequest(limit=body.limit, offset=body.offset),
    )
