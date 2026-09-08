"""The database port (ADR 004).

`Database` is the only thing boundaries (API routes via `app/shared/api.py`,
the background worker, the startup sweep, tests) need to get a scope to run
a module's `Commands`/`Queries` service in. It hands out two kinds:

- `unit_of_work()`: for writes. Backed by a transaction; commits on normal
  exit, rolls back on exception. `app.composition`'s `build_*_commands`
  factories build write-side repositories from the `UnitOfWork`'s session.
- `read_scope()`: for reads. Never opens a write transaction and never
  commits — even if a query mistakenly executes a write through it, nothing
  persists, because the scope always rolls back on exit. This is the
  structural enforcement of "queries can't write" called for in the plan,
  independent of any type-checking discipline.

This port must not expose module-specific command/query types or service
classes — it only knows how to open sessions/scopes.

`UnitOfWork` and `ReadScope` are deliberately opaque marker types here: a
"session" is a SQLAlchemy concept, and this module must stay technology-
agnostic (ADR 004's "concrete database code lives in adapters" — that
includes the database *driver*, not just the SQL dialect). The concrete
adapter (`sqlalchemy_database.py`) attaches a public `session` to its own
`SqlAlchemyUnitOfWork`/`SqlAlchemyReadScope` classes; module-specific
repository/query adapters (e.g. `app/tables/adapters/`) depend on
those concrete classes directly to reach it — a concrete-to-concrete
dependency between two adapter modules, not a leak through this port,
since the composition root passes the concrete scope straight through
without ever needing to know it has a `.session`.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol


class UnitOfWork(Protocol):
    """Opaque handle for one command's transactional scope."""


class ReadScope(Protocol):
    """Opaque handle for one query's read-only scope."""


class Database(Protocol):
    def unit_of_work(self) -> AbstractAsyncContextManager[UnitOfWork]: ...

    def read_scope(self) -> AbstractAsyncContextManager[ReadScope]: ...
