from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from factors.shared.adapters.sqlalchemy_data_access import SqlAlchemyDataAccess
from factors.shared.ports.database import DataAccess, Database


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
    async def transaction(self) -> AsyncIterator[DataAccess]:
        async with self._session_factory() as session, session.begin():
            data_access = SqlAlchemyDataAccess(session)
            try:
                yield data_access
            finally:
                data_access._deactivate()

    @asynccontextmanager
    async def snapshot(self) -> AsyncIterator[DataAccess]:
        async with self._session_factory() as session:
            data_access = SqlAlchemyDataAccess(session)
            try:
                yield data_access
            finally:
                data_access._deactivate()
                await session.rollback()
