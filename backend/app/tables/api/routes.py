"""Thin HTTP boundary: parse input, call the module's use cases, serialize
the result."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.shared.api import get_database
from app.shared.pagination import PageRequest
from app.shared.ports.database import Database
from app.tables.api import schemas
from app.tables.use_cases import TablesUseCases

router = APIRouter()


def get_tables_use_cases(database: Database = Depends(get_database)) -> TablesUseCases:
    return TablesUseCases(database)


@router.post("", status_code=201)
async def create_decision_table(
    body: schemas.CreateDecisionTableRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.create_decision_table(body.name, body.description)


@router.get("")
async def list_decision_tables(
    limit: int = 50,
    offset: int = 0,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.list_decision_tables(PageRequest(limit=limit, offset=offset))


@router.get("/{table_id}")
async def get_decision_table(
    table_id: int, use_cases: TablesUseCases = Depends(get_tables_use_cases)
):
    return await use_cases.get_decision_table(table_id)


@router.patch("/{table_id}")
async def update_decision_table(
    table_id: int,
    body: schemas.UpdateDecisionTableRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    fields = body.model_fields_set
    return await use_cases.update_decision_table(
        table_id=table_id,
        name=body.name,
        description=body.description,
        description_set="description" in fields,
    )


@router.delete("/{table_id}", status_code=204)
async def delete_decision_table(
    table_id: int, use_cases: TablesUseCases = Depends(get_tables_use_cases)
) -> None:
    await use_cases.delete_decision_table(table_id)


@router.post("/{table_id}/factors", status_code=201)
async def add_factor(
    table_id: int,
    body: schemas.AddFactorRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.add_factor(table_id, body.name)


@router.get("/{table_id}/factors")
async def list_factors(
    table_id: int, use_cases: TablesUseCases = Depends(get_tables_use_cases)
):
    return await use_cases.list_factors(table_id)


@router.patch("/{table_id}/factors/{factor_id}")
async def update_factor(
    table_id: int,
    factor_id: int,
    body: schemas.UpdateFactorRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.update_factor(
        table_id=table_id,
        factor_id=factor_id,
        name=body.name,
        order_index=body.order_index,
    )


@router.delete("/{table_id}/factors/{factor_id}", status_code=204)
async def delete_factor(
    table_id: int,
    factor_id: int,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
) -> None:
    await use_cases.delete_factor(table_id, factor_id)


@router.post("/{table_id}/factors/{factor_id}/values", status_code=201)
async def add_factor_value(
    table_id: int,
    factor_id: int,
    body: schemas.AddFactorValueRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.add_factor_value(table_id, factor_id, body.value)


@router.patch("/{table_id}/factors/{factor_id}/values/{value_id}")
async def update_factor_value(
    table_id: int,
    factor_id: int,
    value_id: int,
    body: schemas.UpdateFactorValueRequest,
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
):
    return await use_cases.update_factor_value(
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
    use_cases: TablesUseCases = Depends(get_tables_use_cases),
) -> None:
    await use_cases.delete_factor_value(table_id, factor_id, value_id)
