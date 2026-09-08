"""Thin HTTP boundary: parse input, call the module's command/query
service, serialize the result."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.composition import build_rules_commands, build_rules_queries
from app.rules.api import schemas
from app.rules.commands import RulesCommands
from app.rules.queries import RulesQueries
from app.shared.api import get_read_scope, get_uow
from app.shared.database.port import ReadScope, UnitOfWork
from app.shared.pagination import PageRequest

router = APIRouter()


def get_rules_commands(uow: UnitOfWork = Depends(get_uow)) -> RulesCommands:
    return build_rules_commands(uow)


def get_rules_queries(scope: ReadScope = Depends(get_read_scope)) -> RulesQueries:
    return build_rules_queries(scope)


@router.post("/{table_id}/rules", status_code=201)
async def create_rule(
    table_id: int,
    body: schemas.CreateRuleRequest,
    commands: RulesCommands = Depends(get_rules_commands),
):
    return await commands.create_rule(
        table_id=table_id,
        factor_values=tuple(body.factor_values),
        output=body.output,
        title=body.title,
    )


@router.get("/{table_id}/rules")
async def list_rules(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    queries: RulesQueries = Depends(get_rules_queries),
):
    return await queries.list_rules(
        table_id=table_id, page=PageRequest(limit=limit, offset=offset)
    )


@router.get("/{table_id}/rules/overlaps")
async def list_rule_overlaps(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    queries: RulesQueries = Depends(get_rules_queries),
):
    return await queries.list_rule_overlaps(
        table_id=table_id, page=PageRequest(limit=limit, offset=offset)
    )


@router.patch("/{table_id}/rules/{rule_id}")
async def update_rule(
    table_id: int,
    rule_id: int,
    body: schemas.UpdateRuleRequest,
    commands: RulesCommands = Depends(get_rules_commands),
):
    fields = body.model_fields_set
    return await commands.update_rule(
        table_id=table_id,
        rule_id=rule_id,
        output=body.output,
        title=body.title,
        title_set="title" in fields,
        factor_values=tuple(body.factor_values)
        if body.factor_values is not None
        else None,
        factor_values_set="factor_values" in fields,
    )


@router.delete("/{table_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    table_id: int, rule_id: int, commands: RulesCommands = Depends(get_rules_commands)
) -> None:
    await commands.delete_rule(table_id=table_id, rule_id=rule_id)


@router.post("/{table_id}/rules/reapply")
async def reapply_rules(
    table_id: int, commands: RulesCommands = Depends(get_rules_commands)
):
    return await commands.reapply_rules(table_id)


@router.post("/{table_id}/rules/reorder")
async def reorder_rules(
    table_id: int,
    body: schemas.ReorderRulesRequest,
    commands: RulesCommands = Depends(get_rules_commands),
):
    return await commands.reorder_rules(
        table_id=table_id, ordered_rule_ids=tuple(body.ordered_rule_ids)
    )
