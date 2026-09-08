"""Thin HTTP boundary: parse input, submit a typed request to the mediator,
serialize the result (ADR 007)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.shared.api import get_mediator
from app.shared.mediator.mediator import Mediator
from app.shared.pagination import PageRequest
from app.tables.api import schemas
from app.tables.commands import (
    AddFactorCommand,
    AddFactorValueCommand,
    CreateDecisionTableCommand,
    DeleteDecisionTableCommand,
    DeleteFactorCommand,
    DeleteFactorValueCommand,
    UpdateDecisionTableCommand,
    UpdateFactorCommand,
    UpdateFactorValueCommand,
)
from app.tables.queries import (
    GetDecisionTableQuery,
    ListDecisionTablesQuery,
    ListFactorsQuery,
)

router = APIRouter()


@router.post("", status_code=201)
async def create_decision_table(
    body: schemas.CreateDecisionTableRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(CreateDecisionTableCommand(name=body.name, description=body.description))


@router.get("")
async def list_decision_tables(
    limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(ListDecisionTablesQuery(page=PageRequest(limit=limit, offset=offset)))


@router.get("/{table_id}")
async def get_decision_table(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(GetDecisionTableQuery(table_id=table_id))


@router.patch("/{table_id}")
async def update_decision_table(
    table_id: int,
    body: schemas.UpdateDecisionTableRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        UpdateDecisionTableCommand(
            table_id=table_id,
            name=body.name,
            description=body.description,
            description_set="description" in fields,
        )
    )


@router.delete("/{table_id}", status_code=204)
async def delete_decision_table(table_id: int, mediator: Mediator = Depends(get_mediator)) -> None:
    await mediator.execute(DeleteDecisionTableCommand(table_id=table_id))


@router.post("/{table_id}/factors", status_code=201)
async def add_factor(
    table_id: int, body: schemas.AddFactorRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(AddFactorCommand(table_id=table_id, name=body.name))


@router.get("/{table_id}/factors")
async def list_factors(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(ListFactorsQuery(table_id=table_id))


@router.patch("/{table_id}/factors/{factor_id}")
async def update_factor(
    table_id: int,
    factor_id: int,
    body: schemas.UpdateFactorRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        UpdateFactorCommand(
            table_id=table_id, factor_id=factor_id, name=body.name, order_index=body.order_index
        )
    )


@router.delete("/{table_id}/factors/{factor_id}", status_code=204)
async def delete_factor(
    table_id: int, factor_id: int, mediator: Mediator = Depends(get_mediator)
) -> None:
    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=factor_id))


@router.post("/{table_id}/factors/{factor_id}/values", status_code=201)
async def add_factor_value(
    table_id: int,
    factor_id: int,
    body: schemas.AddFactorValueRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value=body.value)
    )


@router.patch("/{table_id}/factors/{factor_id}/values/{value_id}")
async def update_factor_value(
    table_id: int,
    factor_id: int,
    value_id: int,
    body: schemas.UpdateFactorValueRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        UpdateFactorValueCommand(
            table_id=table_id,
            factor_id=factor_id,
            value_id=value_id,
            value=body.value,
            order_index=body.order_index,
        )
    )


@router.delete("/{table_id}/factors/{factor_id}/values/{value_id}", status_code=204)
async def delete_factor_value(
    table_id: int, factor_id: int, value_id: int, mediator: Mediator = Depends(get_mediator)
) -> None:
    await mediator.execute(
        DeleteFactorValueCommand(table_id=table_id, factor_id=factor_id, value_id=value_id)
    )
