"""The `UnitOfWork` port (ADR 004) — one open transaction's worth of every
module's write-side repository (`uow.tables`, `uow.jobs`, `uow.combinations`,
`uow.rules`).

Declared as abstract-port-typed attributes (not raw sessions), so use-case
code never imports SQLAlchemy or any concrete adapter class — it only ever
sees the abstract repository port each attribute is typed with. The concrete
implementation (`adapters/sqlalchemy_unit_of_work.py`) is the one place that
constructs the concrete adapters and attaches them.

This means this module imports every module's `ports/` (for these type
annotations) — a deliberate, acknowledged relaxation of ADR 003's "shared/
must not hold domain behavior that belongs to one context": this app is
genuinely one bounded context split into modules for file size, not several
true DDD-separate contexts. Worth its own ADR rather than letting ADR 003
quietly go stale.
"""

from typing import Protocol

from app.combinations.ports.combination_repository import CombinationRepository
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.rules.ports.rule_repository import RuleRepository
from app.tables.ports.decision_table_repository import DecisionTableRepository


class UnitOfWork(Protocol):
    """One transaction's worth of every module's write-side repository."""

    tables: DecisionTableRepository
    jobs: GenerationJobRepository
    combinations: CombinationRepository
    rules: RuleRepository
