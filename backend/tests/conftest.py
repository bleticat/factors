"""Per ADR 005: each test gets its own fresh database, migrated the same
way production is (Alembic `upgrade head`, not `create_all`), destroyed
after. The `database` fixture is a real `SqlAlchemyDatabase`, the same
concrete type `app/main.py` builds — tests call the same module `Commands`/
`Queries` service classes (via `app.composition`'s factory functions and
`app.shared.execution`'s `run_command`/`run_query`) that production
boundaries use, so tests can't drift from production wiring.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.shared.database.sqlalchemy_database import SqlAlchemyDatabase, create_engine

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture
def database() -> Iterator[SqlAlchemyDatabase]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    built = SqlAlchemyDatabase(engine)

    yield built

    asyncio.run(engine.dispose())
    os.remove(path)
