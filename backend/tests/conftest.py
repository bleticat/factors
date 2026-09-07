"""Per ADR 005: each test gets its own fresh database, migrated the same
way production is (Alembic `upgrade head`, not `create_all`), destroyed
after. The `mediator` fixture is built via the *same* `composition.
build_mediator` used by `app/main.py`, so tests can't drift from production
wiring — tests execute command/query requests through the mediator, the
same lifecycle application code uses.
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
from app.composition import build_mediator
from app.shared.database.sqlalchemy_database import SqlAlchemyDatabase, create_engine
from app.shared.mediator.mediator import Mediator

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEST_MAX_COMBINATIONS = 1000


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture
def mediator() -> Iterator[Mediator]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    database = SqlAlchemyDatabase(engine)
    built = build_mediator(database, max_combinations=DEFAULT_TEST_MAX_COMBINATIONS)

    yield built

    asyncio.run(engine.dispose())
    os.remove(path)


@pytest.fixture
def low_cap_mediator() -> Iterator[Mediator]:
    """A mediator wired with a tiny `max_combinations` cap, for testing the
    generation cap-rejection path without generating a huge fixture table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    database = SqlAlchemyDatabase(engine)
    built = build_mediator(database, max_combinations=10)

    yield built

    asyncio.run(engine.dispose())
    os.remove(path)
