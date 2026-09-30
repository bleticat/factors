"""SQLAlchemy async implementation of the `UnitOfWork` port — the sole
place that wires every feature's concrete write-side repository adapters
together (see `app/application/ports/unit_of_work.py`'s docstring for why
that's a deliberate exception to feature-owned code otherwise staying out
of cross-cutting files).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.combinations.repository import (
    SqlAlchemyCombinationRepository,
)
from app.adapters.outbound.persistence.generation.repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.adapters.outbound.persistence.rules.repository import SqlAlchemyRuleRepository
from app.adapters.outbound.persistence.tables.repository import (
    SqlAlchemyDecisionTableRepository,
)
from app.application.ports.unit_of_work import UnitOfWork


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
