"""SQLAlchemy async implementation of the `UnitOfWork` port — the sole
place that wires every module's concrete write-side repository adapters
together (see `app/shared/ports/unit_of_work.py`'s docstring for why that's
an acknowledged exception to ADR 003's shared/-stays-generic rule rather
than a leak).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.combinations.adapters.sqlalchemy_combination_repository import (
    SqlAlchemyCombinationRepository,
)
from app.generation.adapters.sqlalchemy_generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.rules.adapters.sqlalchemy_rule_repository import SqlAlchemyRuleRepository
from app.shared.ports.unit_of_work import UnitOfWork
from app.tables.adapters.sqlalchemy_decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """One open transaction's repositories, all bound to the same
    `AsyncSession` — so cross-module writes inside one use-case method
    (e.g. `TablesUseCases.delete_factor` cascading into `combinations`/
    `rules`) share that one transaction automatically."""

    def __init__(self, session: AsyncSession) -> None:
        self.tables = SqlAlchemyDecisionTableRepository(session)
        self.jobs = SqlAlchemyGenerationJobRepository(session)
        self.combinations = SqlAlchemyCombinationRepository(session)
        self.rules = SqlAlchemyRuleRepository(session)
