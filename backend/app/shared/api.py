"""Cross-context FastAPI wiring shared by every module's `api/routes.py`:
resolves the app's `Database` and, from it, a per-request unit of
work/read scope. Non-FastAPI callers (the background worker, the startup
sweep, tests) can't use `Depends`; see `app/shared/execution.py` for their
equivalent."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request

from app.shared.database.port import Database, ReadScope, UnitOfWork


def get_database(request: Request) -> Database:
    return request.app.state.database


async def get_uow(
    database: Database = Depends(get_database),
) -> AsyncIterator[UnitOfWork]:
    async with database.unit_of_work() as uow:
        yield uow


async def get_read_scope(
    database: Database = Depends(get_database),
) -> AsyncIterator[ReadScope]:
    async with database.read_scope() as scope:
        yield scope
