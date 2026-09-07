"""SQLAlchemy async implementation of the `Database` port."""

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

from app.shared.database.port import Database, ReadScope, UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


class SqlAlchemyReadScope(ReadScope):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


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

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncIterator[UnitOfWork]:
        async with self._session_factory() as session, session.begin():
            yield SqlAlchemyUnitOfWork(session)

    @asynccontextmanager
    async def read_scope(self) -> AsyncIterator[ReadScope]:
        async with self._session_factory() as session:
            try:
                yield SqlAlchemyReadScope(session)
            finally:
                # Never commit on the read path, even if a handler
                # mistakenly wrote through it (see port.py docstring).
                await session.rollback()
