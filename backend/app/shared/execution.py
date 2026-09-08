"""Scope helpers for callers that can't use FastAPI's `Depends` — the
background generation worker, the startup sweep, and tests. `api/routes.py`
files use `Depends(get_uow)`/`Depends(get_read_scope)` instead (see
`app/shared/api.py`); both ultimately open the same `Database` scopes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.shared.database.port import Database, ReadScope, UnitOfWork

TResult = TypeVar("TResult")


async def run_command(
    database: Database, fn: Callable[[UnitOfWork], Awaitable[TResult]]
) -> TResult:
    async with database.unit_of_work() as uow:
        return await fn(uow)


async def run_query(
    database: Database, fn: Callable[[ReadScope], Awaitable[TResult]]
) -> TResult:
    async with database.read_scope() as scope:
        return await fn(scope)
