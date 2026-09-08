"""Thin HTTP boundary: parse input, call the module's command/query
service, serialize the result."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.composition import build_tables_commands, build_tables_queries
from app.shared.api import get_read_scope, get_uow
from app.shared.database.port import ReadScope, UnitOfWork
from app.shared.pagination import PageRequest
from app.tables.api import schemas
from app.tables.commands import TablesCommands
from app.tables.queries import TablesQueries

router = APIRouter()


def get_tables_commands(uow: UnitOfWork = Depends(get_uow)) -> TablesCommands:
    return build_tables_commands(uow)


def get_tables_queries(scope: ReadScope = Depends(get_read_scope)) -> TablesQueries:
    return build_tables_queries(scope)


@router.post("", status_code=201)
async def create_decision_table(
    body: schemas.CreateDecisionTableRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    return await commands.create_decision_table(body.name, body.description)


@router.get("")
async def list_decision_tables(
    limit: int = 50,
    offset: int = 0,
    queries: TablesQueries = Depends(get_tables_queries),
):
    return await queries.list_decision_tables(PageRequest(limit=limit, offset=offset))


@router.get("/{table_id}")
async def get_decision_table(
    table_id: int, queries: TablesQueries = Depends(get_tables_queries)
):
    return await queries.get_decision_table(table_id)


@router.patch("/{table_id}")
async def update_decision_table(
    table_id: int,
    body: schemas.UpdateDecisionTableRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    fields = body.model_fields_set
    return await commands.update_decision_table(
        table_id=table_id,
        name=body.name,
        description=body.description,
        description_set="description" in fields,
    )


@router.delete("/{table_id}", status_code=204)
async def delete_decision_table(
    table_id: int, commands: TablesCommands = Depends(get_tables_commands)
) -> None:
    await commands.delete_decision_table(table_id)


@router.post("/{table_id}/factors", status_code=201)
async def add_factor(
    table_id: int,
    body: schemas.AddFactorRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    return await commands.add_factor(table_id, body.name)


@router.get("/{table_id}/factors")
async def list_factors(
    table_id: int, queries: TablesQueries = Depends(get_tables_queries)
):
    return await queries.list_factors(table_id)


@router.patch("/{table_id}/factors/{factor_id}")
async def update_factor(
    table_id: int,
    factor_id: int,
    body: schemas.UpdateFactorRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    return await commands.update_factor(
        table_id=table_id,
        factor_id=factor_id,
        name=body.name,
        order_index=body.order_index,
    )


@router.delete("/{table_id}/factors/{factor_id}", status_code=204)
async def delete_factor(
    table_id: int,
    factor_id: int,
    commands: TablesCommands = Depends(get_tables_commands),
) -> None:
    await commands.delete_factor(table_id, factor_id)


@router.post("/{table_id}/factors/{factor_id}/values", status_code=201)
async def add_factor_value(
    table_id: int,
    factor_id: int,
    body: schemas.AddFactorValueRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    return await commands.add_factor_value(table_id, factor_id, body.value)


@router.patch("/{table_id}/factors/{factor_id}/values/{value_id}")
async def update_factor_value(
    table_id: int,
    factor_id: int,
    value_id: int,
    body: schemas.UpdateFactorValueRequest,
    commands: TablesCommands = Depends(get_tables_commands),
):
    return await commands.update_factor_value(
        table_id=table_id,
        factor_id=factor_id,
        value_id=value_id,
        value=body.value,
        order_index=body.order_index,
    )


@router.delete("/{table_id}/factors/{factor_id}/values/{value_id}", status_code=204)
async def delete_factor_value(
    table_id: int,
    factor_id: int,
    value_id: int,
    commands: TablesCommands = Depends(get_tables_commands),
) -> None:
    await commands.delete_factor_value(table_id, factor_id, value_id)
