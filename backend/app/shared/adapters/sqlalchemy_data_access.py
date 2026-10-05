"""SQLAlchemy async implementation of the `DataAccess` port — the sole
place that wires every module's concrete repository/reader adapters
together (see `app/shared/ports/database.py`'s docstring for why that's an
acknowledged exception to ADR 003's shared/-stays-generic rule rather than
a leak).
"""

from typing import NoReturn

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


class _ExpiredDataAccess:
    """What every repository/reader attribute on a `SqlAlchemyDataAccess`
    is replaced with once its owning `transaction()`/`snapshot()` block
    exits (see `_deactivate` below). Any further use — a `db` reference a
    use-case method kept past its `async with`, or passed outward instead
    of being used inside it — hits this instead of the real adapter, and
    fails loudly and immediately rather than running one more query against
    a session that's already been committed/rolled back and returned to
    the pool."""

    def __init__(self, attr_name: str) -> None:
        self._attr_name = attr_name

    def __getattr__(self, _name: str) -> NoReturn:
        raise RuntimeError(
            f"DataAccess.{self._attr_name} was used outside the "
            "`transaction()`/`snapshot()` block that opened it. Every "
            "db.tables/db.rules/db.*_reader call must happen inside that "
            "`async with` — don't store `db` on self or return it from the "
            "block."
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

    def _deactivate(self) -> None:
        """Called by `SqlAlchemyDatabase.transaction()`/`snapshot()` the
        instant their `async with` block's body returns — before the
        underlying session is committed/rolled back and closed."""
        self.tables = _ExpiredDataAccess("tables")
        self.jobs = _ExpiredDataAccess("jobs")
        self.combinations = _ExpiredDataAccess("combinations")
        self.rules = _ExpiredDataAccess("rules")
        self.tables_reader = _ExpiredDataAccess("tables_reader")
        self.combinations_reader = _ExpiredDataAccess("combinations_reader")
        self.rules_reader = _ExpiredDataAccess("rules_reader")
        self.jobs_reader = _ExpiredDataAccess("jobs_reader")
