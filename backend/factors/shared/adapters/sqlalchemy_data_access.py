from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from factors.features.combinations.adapters.sqlalchemy.combination_reader import (
    SqlAlchemyCombinationReader,
)
from factors.features.combinations.adapters.sqlalchemy.combination_repository import (
    SqlAlchemyCombinationRepository,
)
from factors.features.generation.adapters.sqlalchemy.generation_job_reader import (
    SqlAlchemyGenerationJobReader,
)
from factors.features.generation.adapters.sqlalchemy.generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from factors.features.rules.adapters.sqlalchemy.rule_reader import SqlAlchemyRuleReader
from factors.features.rules.adapters.sqlalchemy.rule_repository import (
    SqlAlchemyRuleRepository,
)
from factors.features.tables.adapters.sqlalchemy.decision_table_reader import (
    SqlAlchemyDecisionTableReader,
)
from factors.features.tables.adapters.sqlalchemy.decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)
from factors.shared.ports.database import DataAccess


class _ExpiredDataAccess:
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
    def __init__(self, session: AsyncSession) -> None:
        self.tables = SqlAlchemyDecisionTableRepository(session)
        self.jobs = SqlAlchemyGenerationJobRepository(session)
        self.combinations = SqlAlchemyCombinationRepository(session)
        self.rules = SqlAlchemyRuleRepository(session)

        self.tables_reader = SqlAlchemyDecisionTableReader(session)
        self.combinations_reader = SqlAlchemyCombinationReader(session)
        self.rules_reader = SqlAlchemyRuleReader(session)
        self.jobs_reader = SqlAlchemyGenerationJobReader(session)

    def _deactivate(self) -> None:
        self.tables = _ExpiredDataAccess("tables")
        self.jobs = _ExpiredDataAccess("jobs")
        self.combinations = _ExpiredDataAccess("combinations")
        self.rules = _ExpiredDataAccess("rules")
        self.tables_reader = _ExpiredDataAccess("tables_reader")
        self.combinations_reader = _ExpiredDataAccess("combinations_reader")
        self.rules_reader = _ExpiredDataAccess("rules_reader")
        self.jobs_reader = _ExpiredDataAccess("jobs_reader")
