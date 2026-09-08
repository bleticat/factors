"""Thin HTTP boundary: parse input, submit a typed request to the mediator,
serialize the result (ADR 007)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.rules.api import schemas
from app.rules.commands import (
    CreateRuleCommand,
    DeleteRuleCommand,
    ReapplyRulesCommand,
    ReorderRulesCommand,
    UpdateRuleCommand,
)
from app.rules.queries import ListRuleOverlapsQuery, ListRulesQuery
from app.shared.api import get_mediator
from app.shared.mediator.mediator import Mediator
from app.shared.pagination import PageRequest

router = APIRouter()


@router.post("/{table_id}/rules", status_code=201)
async def create_rule(
    table_id: int, body: schemas.CreateRuleRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=tuple(body.factor_values),
            output=body.output,
            title=body.title,
        )
    )


@router.get("/{table_id}/rules")
async def list_rules(
    table_id: int, limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ListRulesQuery(table_id=table_id, page=PageRequest(limit=limit, offset=offset))
    )


@router.get("/{table_id}/rules/overlaps")
async def list_rule_overlaps(
    table_id: int, limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ListRuleOverlapsQuery(table_id=table_id, page=PageRequest(limit=limit, offset=offset))
    )


@router.patch("/{table_id}/rules/{rule_id}")
async def update_rule(
    table_id: int,
    rule_id: int,
    body: schemas.UpdateRuleRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        UpdateRuleCommand(
            table_id=table_id,
            rule_id=rule_id,
            output=body.output,
            title=body.title,
            title_set="title" in fields,
            factor_values=tuple(body.factor_values) if body.factor_values is not None else None,
            factor_values_set="factor_values" in fields,
        )
    )


@router.delete("/{table_id}/rules/{rule_id}", status_code=204)
async def delete_rule(table_id: int, rule_id: int, mediator: Mediator = Depends(get_mediator)) -> None:
    await mediator.execute(DeleteRuleCommand(table_id=table_id, rule_id=rule_id))


@router.post("/{table_id}/rules/reapply")
async def reapply_rules(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(ReapplyRulesCommand(table_id=table_id))


@router.post("/{table_id}/rules/reorder")
async def reorder_rules(
    table_id: int, body: schemas.ReorderRulesRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ReorderRulesCommand(table_id=table_id, ordered_rule_ids=tuple(body.ordered_rule_ids))
    )
