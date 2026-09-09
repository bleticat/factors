"""The database port (ADR 004).

`Database` is the only thing use-case classes need to do their work: it
exposes `unit_of_work()` for writes (one transaction per call — a use
case's own methods decide when to open one, and may open more than one if
it genuinely has independent-commit steps), and holds every module's
read-side `...Queries` service directly as a long-lived attribute
(`database.tables_queries`, `database.rules_queries`, ...). There is no
separate per-call "read scope" concept — a query method's own internal
session open/close already gives it everything a scope used to provide,
and nothing in any `Queries` adapter ever writes.

`UnitOfWork` holds every module's write-side repository as an attribute
(`uow.tables`, `uow.jobs`, `uow.combinations`, `uow.rules`) — one per open
transaction.

Both `UnitOfWork` and `Database` declare these as abstract-port-typed
attributes (not raw sessions), so use-case code never imports SQLAlchemy
or any concrete adapter class — it only ever sees the abstract repository/
query ports each attribute is typed with. The concrete implementation
(`sqlalchemy_database.py`) is the one place that constructs the concrete
adapters and attaches them.

This means `port.py` itself now imports every module's `ports/` (for these
type annotations) — a deliberate, acknowledged relaxation of ADR 003's
"shared/ must not hold domain behavior that belongs to one context": this
app is genuinely one bounded context split into modules for file size, not
several true DDD-separate contexts. Worth its own ADR rather than letting
ADR 003 quietly go stale.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.combinations.ports.combination_queries import CombinationQueries
from app.combinations.ports.combination_repository import CombinationRepository
from app.generation.ports.generation_job_queries import GenerationJobQueries
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.rules.ports.rule_queries import RuleQueries
from app.rules.ports.rule_repository import RuleRepository
from app.tables.ports.decision_table_queries import DecisionTableQueries
from app.tables.ports.decision_table_repository import DecisionTableRepository


class UnitOfWork(Protocol):
    """One transaction's worth of every module's write-side repository."""

    tables: DecisionTableRepository
    jobs: GenerationJobRepository
    combinations: CombinationRepository
    rules: RuleRepository


class Database(Protocol):
    """Long-lived — constructed once at app startup, not per request."""

    tables_queries: DecisionTableQueries
    combinations_queries: CombinationQueries
    rules_queries: RuleQueries
    jobs_queries: GenerationJobQueries

    def unit_of_work(self) -> AbstractAsyncContextManager[UnitOfWork]: ...
