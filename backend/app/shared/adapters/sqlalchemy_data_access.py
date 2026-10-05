"""SQLAlchemy async implementation of the `DataAccess` port — the sole
place that wires every module's concrete repository/reader adapters
together (see `app/shared/ports/database.py`'s docstring for why that's an
acknowledged exception to ADR 003's shared/-stays-generic rule rather than
a leak).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.combinations.adapters.sqlalchemy_combination_reader import (
    SqlAlchemyCombinationReader,
)
from app.combinations.adapters.sqlalchemy_combination_repository import (
    SqlAlchemyCombinationRepository,
)
from app.generation.adapters.sqlalchemy_generation_job_reader import (
    SqlAlchemyGenerationJobReader,
)
from app.generation.adapters.sqlalchemy_generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.rules.adapters.sqlalchemy_rule_reader import SqlAlchemyRuleReader
from app.rules.adapters.sqlalchemy_rule_repository import SqlAlchemyRuleRepository
from app.shared.ports.database import DataAccess
from app.tables.adapters.sqlalchemy_decision_table_reader import (
    SqlAlchemyDecisionTableReader,
)
from app.tables.adapters.sqlalchemy_decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)


class SqlAlchemyDataAccess(DataAccess):
    """One open session's repositories and readers, all bound to the same
    `AsyncSession` — so cross-module writes inside one use-case method
    (e.g. `TablesUseCases.delete_factor` cascading into `combinations`/
    `rules`) share that one transaction automatically, and a reader called
    from the same block sees whatever that block already wrote."""

    def __init__(self, session: AsyncSession) -> None:
        """Wire every module's repository and reader to the same `session`."""
        self.tables = SqlAlchemyDecisionTableRepository(session)
        self.jobs = SqlAlchemyGenerationJobRepository(session)
        self.combinations = SqlAlchemyCombinationRepository(session)
        self.rules = SqlAlchemyRuleRepository(session)

        self.tables_reader = SqlAlchemyDecisionTableReader(session)
        self.combinations_reader = SqlAlchemyCombinationReader(session)
        self.rules_reader = SqlAlchemyRuleReader(session)
        self.jobs_reader = SqlAlchemyGenerationJobReader(session)
