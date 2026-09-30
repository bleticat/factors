"""The `UnitOfWork` port — one open transaction's worth of every feature's
write-side repository (`uow.tables`, `uow.jobs`, `uow.combinations`,
`uow.rules`).

Declared as abstract-port-typed attributes (not raw sessions), so use-case
code never imports SQLAlchemy or any concrete adapter class — it only ever
sees the abstract repository port each attribute is typed with. The concrete
implementation (`adapters/sqlalchemy_unit_of_work.py`) is the one place that
constructs the concrete adapters and attaches them.

This means this module imports every feature's `ports/` (for these type
annotations) — a deliberate exception to feature-owned code otherwise
staying out of cross-cutting files: this app is genuinely one bounded
context split into feature folders for file size, not several true
DDD-separate contexts.
"""

from __future__ import annotations

from typing import Protocol

from app.application.combinations.ports.repository import CombinationRepository
from app.application.generation.ports.repository import GenerationJobRepository
from app.application.rules.ports.repository import RuleRepository
from app.application.tables.ports.repository import DecisionTableRepository


class UnitOfWork(Protocol):
    """One transaction's worth of every module's write-side repository."""

    tables: DecisionTableRepository
    jobs: GenerationJobRepository
    combinations: CombinationRepository
    rules: RuleRepository
