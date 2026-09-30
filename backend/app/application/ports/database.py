"""The `Database` port.

`Database` is the only thing use-case classes need to do their work: it
exposes `unit_of_work()` for writes (one transaction per call — a use
case's own methods decide when to open one, and may open more than one if
it genuinely has independent-commit steps), and holds every module's
read-side `...Queries` service directly as a long-lived attribute
(`database.tables_queries`, `database.rules_queries`, ...). There is no
separate per-call "read scope" concept — a query method's own internal
session open/close already gives it everything a scope used to provide,
and nothing in any `Queries` adapter ever writes.

Declared as abstract-port-typed attributes (not raw sessions), so use-case
code never imports SQLAlchemy or any concrete adapter class — it only ever
sees the abstract query port each attribute is typed with. The concrete
implementation (`adapters/sqlalchemy_database.py`) is the one place that
constructs the concrete adapters and attaches them.

This means this module imports every feature's `ports/` (for these type
annotations) — a deliberate exception to feature-owned code otherwise
staying out of cross-cutting files: this app is genuinely one bounded
context split into feature folders for file size, not several true
DDD-separate contexts.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.application.combinations.ports.queries import CombinationQueries
from app.application.generation.ports.queries import GenerationJobQueries
from app.application.ports.unit_of_work import UnitOfWork
from app.application.rules.ports.queries import RuleQueries
from app.application.tables.ports.queries import DecisionTableQueries


class Database(Protocol):
    """Long-lived — constructed once at app startup, not per request."""

    tables_queries: DecisionTableQueries
    combinations_queries: CombinationQueries
    rules_queries: RuleQueries
    jobs_queries: GenerationJobQueries

    def unit_of_work(self) -> AbstractAsyncContextManager[UnitOfWork]: ...
