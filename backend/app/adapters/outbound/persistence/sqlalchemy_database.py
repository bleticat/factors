"""SQLAlchemy async implementation of the `Database` port — the sole place
that wires every feature's concrete read-side query adapters together.
This is a deliberate exception to feature-owned code otherwise staying out
of shared/cross-cutting files: the app is one bounded context split into
feature folders for file size, not several independent contexts, so one
`Database` aggregating every feature's queries isn't crossing a true
context boundary.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.adapters.outbound.persistence.combinations.queries import (
    SqlAlchemyCombinationQueries,
)
from app.adapters.outbound.persistence.generation.queries import (
    SqlAlchemyGenerationJobQueries,
)
from app.adapters.outbound.persistence.rules.queries import SqlAlchemyRuleQueries
from app.adapters.outbound.persistence.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.adapters.outbound.persistence.tables.queries import (
    SqlAlchemyDecisionTableQueries,
)
from app.application.ports.database import Database
from app.application.ports.unit_of_work import UnitOfWork


def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url, future=True)

    if database_url.startswith("sqlite"):
        # WAL so status-polling reads don't block behind the generation-job
        # writer; foreign_keys=ON since SQLite disables FK enforcement by
        # default per-connection.
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


class SqlAlchemyDatabase(Database):
    def __init__(self, engine: AsyncEngine) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=engine, expire_on_commit=False
        )
        # Long-lived — each Queries adapter opens/closes its own session
        # per call (see their `__init__`s), so there's no per-request
        # "read scope" to manage here.
        self.tables_queries = SqlAlchemyDecisionTableQueries(self._session_factory)
        self.combinations_queries = SqlAlchemyCombinationQueries(self._session_factory)
        self.rules_queries = SqlAlchemyRuleQueries(self._session_factory)
        self.jobs_queries = SqlAlchemyGenerationJobQueries(self._session_factory)

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncIterator[UnitOfWork]:
        async with self._session_factory() as session, session.begin():
            yield SqlAlchemyUnitOfWork(session)
