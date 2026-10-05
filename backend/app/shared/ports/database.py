"""The `Database` port (ADR 004, refined by ADR 008).

`Database` is the only thing use-case classes need to do their work: it
opens a `DataAccess` — one object holding every module's write-side
repository (`db.tables`, `db.jobs`, `db.combinations`, `db.rules`) *and*
every module's read-side reader (`db.tables_reader`, `db.rules_reader`, ...)
bound to the same underlying session, so a read inside a block always sees
that block's own uncommitted writes.

There are two ways to open one, matching the two things a use-case method
ever needs:

- `transaction()` for a write (plus any reads it needs along the way) —
  one unit of work, one transaction, one commit on clean exit, rollback on
  exception. A use case opens as many of these as it genuinely has
  independent-commit steps.
- `snapshot()` for a read-only method — one consistent view, always
  rolled back, never committed. Every read opens one, even a method that
  only makes a single reader call: a reader only exists inside an opened
  `DataAccess`, so there's no bare `database.tables_reader` to fall back
  to. What `snapshot()` buys a multi-read method (e.g. a page of rules
  plus an unpaginated pass over every rule to compute shadowing) is that
  every read in the block sees the same view, rather than each opening its
  own connection and risking a result that doesn't agree with the others.

Declared as abstract-port-typed attributes (not raw sessions), so use-case
code never imports SQLAlchemy or any concrete adapter class — it only ever
sees the abstract repository/reader port each attribute is typed with. The
concrete implementation (`adapters/sqlalchemy_database.py`,
`adapters/sqlalchemy_data_access.py`) is the one place that constructs the
concrete adapters and attaches them.

This means this module imports every module's `ports/` (for these type
annotations) — a deliberate, acknowledged relaxation of ADR 003's "shared/
must not hold domain behavior that belongs to one context": this app is
genuinely one bounded context split into modules for file size, not several
true DDD-separate contexts. See ADR 007 (and ADR 008, which refines it) for
why that's its own recorded decision rather than letting ADR 003 quietly go
stale.
"""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.combinations.ports.combination_reader import CombinationReader
from app.combinations.ports.combination_repository import CombinationRepository
from app.generation.ports.generation_job_reader import GenerationJobReader
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.rules.ports.rule_reader import RuleReader
from app.rules.ports.rule_repository import RuleRepository
from app.tables.ports.decision_table_reader import DecisionTableReader
from app.tables.ports.decision_table_repository import DecisionTableRepository


class DataAccess(Protocol):
    """One open session's worth of every module's repository and reader,
    all bound to the same transaction — so a read never falls behind a
    write made earlier in the same block, regardless of which module
    either one belongs to."""

    tables: DecisionTableRepository
    jobs: GenerationJobRepository
    combinations: CombinationRepository
    rules: RuleRepository

    tables_reader: DecisionTableReader
    combinations_reader: CombinationReader
    rules_reader: RuleReader
    jobs_reader: GenerationJobReader


class Database(Protocol):
    """Long-lived — constructed once at app startup, not per request."""

    def transaction(self) -> AbstractAsyncContextManager[DataAccess]:
        """Open one database transaction and yield a `DataAccess` bound to
        it; commits on clean exit, rolls back on exception."""
        ...

    def snapshot(self) -> AbstractAsyncContextManager[DataAccess]:
        """Open one consistent read-only view and yield a `DataAccess`
        bound to it; always rolls back, even if a query mistakenly writes
        through it. Use this instead of `transaction()` when a read method
        makes more than one call that must agree with each other — a
        single call straight through to a reader doesn't need either."""
        ...
