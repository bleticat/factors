"""The database port (ADR 004).

`Database` is the only thing the composition root needs to build the
mediator. It hands out two kinds of execution scope:

- `unit_of_work()`: for commands. Backed by a transaction; commits on normal
  exit, rolls back on exception. Command handler factories build write-side
  repositories from the `UnitOfWork`'s session.
- `read_scope()`: for queries. Never opens a write transaction and never
  commits — even if a query handler mistakenly executes a write through it,
  nothing persists, because the scope always rolls back on exit. This is the
  structural enforcement of "queries can't write" called for in the plan,
  independent of any type-checking discipline.

This port must not expose bounded-context command/query request types,
handlers, or handler factories (ADR 007 guardrail) — it only knows how to
open sessions/scopes.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork(Protocol):
    session: AsyncSession


class ReadScope(Protocol):
    session: AsyncSession


class Database(Protocol):
    def unit_of_work(self) -> AbstractAsyncContextManager[UnitOfWork]: ...

    def read_scope(self) -> AbstractAsyncContextManager[ReadScope]: ...
