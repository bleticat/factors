"""Thin HTTP boundary: parse input, submit a typed request to the mediator,
serialize the result (ADR 007)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.combinations.api import schemas
from app.combinations.commands import (
    BulkFilterInput,
    BulkPatchCombinationsCommand,
    BulkPatchInput,
    PatchCombinationCommand,
)
from app.combinations.queries import EvaluateCombinationsQuery, ListCombinationsQuery
from app.shared.api import get_mediator
from app.shared.mediator.mediator import Mediator
from app.shared.pagination import PageRequest

router = APIRouter()


@router.get("/{table_id}/combinations")
async def list_combinations(
    table_id: int,
    status: str | None = None,
    fv: list[str] = Query(default_factory=list),
    limit: int = 50,
    offset: int = 0,
    mediator: Mediator = Depends(get_mediator),
):
    """`fv` is a repeatable `factor_id:factor_value_id` pair, e.g.
    `?fv=3:9&fv=5:14` — the same AND-ed filter shape bulk-patch uses."""
    return await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            status=status,
            factor_values=tuple(_parse_factor_value_pair(pair) for pair in fv),
            page=PageRequest(limit=limit, offset=offset),
        )
    )


def _parse_factor_value_pair(pair: str) -> tuple[int, int]:
    factor_id_str, _, value_id_str = pair.partition(":")
    return int(factor_id_str), int(value_id_str)


@router.patch("/{table_id}/combinations/{combination_id}")
async def patch_combination(
    table_id: int,
    combination_id: int,
    body: schemas.PatchCombinationRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        PatchCombinationCommand(
            table_id=table_id,
            combination_id=combination_id,
            status=body.status,
            output=body.output,
            output_set="output" in fields,
            impossible_reason=body.impossible_reason,
            impossible_reason_set="impossible_reason" in fields,
        )
    )


@router.post("/{table_id}/combinations/bulk-patch")
async def bulk_patch_combinations(
    table_id: int,
    body: schemas.BulkPatchCombinationsRequest,
    mediator: Mediator = Depends(get_mediator),
):
    patch_fields = body.patch.model_fields_set
    return await mediator.execute(
        BulkPatchCombinationsCommand(
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
    )


@router.post("/{table_id}/evaluate")
async def evaluate(
    table_id: int, body: schemas.EvaluateRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        EvaluateCombinationsQuery(
            table_id=table_id,
            assignment=tuple(body.assignment),
            page=PageRequest(limit=body.limit, offset=body.offset),
        )
    )
