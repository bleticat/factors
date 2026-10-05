"""SQLAlchemy async implementation of the `Database` port (ADR 004).
`Database` holds no long-lived reader instances — each
`transaction()`/`snapshot()` call opens its own session and builds a fresh
`SqlAlchemyDataAccess` bound to it, so there is nothing left to wire up at
construction time beyond the engine's session factory.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.adapters.sqlalchemy_data_access import SqlAlchemyDataAccess
from app.shared.ports.database import DataAccess, Database


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

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[DataAccess]:
        """Open one database transaction and yield a `DataAccess` bound to
        it; commits on clean exit, rolls back on exception. The yielded
        `DataAccess` is deactivated the instant the caller's `async with`
        block exits — any later use of a `db` reference kept past that
        point raises `RuntimeError` rather than running against a session
        that's already been committed and closed (see
        `SqlAlchemyDataAccess._deactivate`)."""
        async with self._session_factory() as session, session.begin():
            data_access = SqlAlchemyDataAccess(session)
            try:
                yield data_access
            finally:
                data_access._deactivate()

    @asynccontextmanager
    async def snapshot(self) -> AsyncIterator[DataAccess]:
        """Open one consistent read-only view and yield a `DataAccess`
        bound to it; always rolls back, even if a query mistakenly writes
        through it. Deactivated on exit, same as `transaction()` above."""
        async with self._session_factory() as session:
            data_access = SqlAlchemyDataAccess(session)
            try:
                yield data_access
            finally:
                data_access._deactivate()
                await session.rollback()
