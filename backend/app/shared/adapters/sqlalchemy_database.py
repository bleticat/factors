"""SQLAlchemy async implementation of the `Database` port — the sole place
that wires every module's concrete read-side query adapters together
(absorbing what a separate composition-root file used to do; see
`app/shared/ports/database.py`'s docstring for why that's an acknowledged
exception to ADR 003's shared/-stays-generic rule rather than a leak).
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

from app.combinations.adapters.sqlalchemy_combination_queries import (
    SqlAlchemyCombinationQueries,
)
from app.generation.adapters.sqlalchemy_generation_job_queries import (
    SqlAlchemyGenerationJobQueries,
)
from app.rules.adapters.sqlalchemy_rule_queries import SqlAlchemyRuleQueries
from app.shared.adapters.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.shared.ports.database import Database
from app.shared.ports.unit_of_work import UnitOfWork
from app.tables.adapters.sqlalchemy_decision_table_queries import (
    SqlAlchemyDecisionTableQueries,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create the app's async SQLAlchemy engine, applying SQLite-specific
    pragmas (WAL, foreign keys, busy timeout) when `database_url` is sqlite."""
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
        """Open one database transaction and yield a `UnitOfWork` bound to
        it; commits on clean exit, rolls back on exception."""
        async with self._session_factory() as session, session.begin():
            yield SqlAlchemyUnitOfWork(session)
