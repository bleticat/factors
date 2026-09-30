"""The `Database` port (ADR 004).

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

This means this module imports every module's `ports/` (for these type
annotations) — a deliberate, acknowledged relaxation of ADR 003's "shared/
must not hold domain behavior that belongs to one context": this app is
genuinely one bounded context split into modules for file size, not several
true DDD-separate contexts. Worth its own ADR rather than letting ADR 003
quietly go stale.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.combinations.ports.combination_queries import CombinationQueries
from app.generation.ports.generation_job_queries import GenerationJobQueries
from app.rules.ports.rule_queries import RuleQueries
from app.shared.ports.unit_of_work import UnitOfWork
from app.tables.ports.decision_table_queries import DecisionTableQueries


class Database(Protocol):
    """Long-lived — constructed once at app startup, not per request."""

    tables_queries: DecisionTableQueries
    combinations_queries: CombinationQueries
    rules_queries: RuleQueries
    jobs_queries: GenerationJobQueries

    def unit_of_work(self) -> AbstractAsyncContextManager[UnitOfWork]:
        """Open one transaction's worth of every module's write-side
        repository, committing on clean exit and rolling back on exception."""
        ...
