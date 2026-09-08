"""The composition root: the one place that knows every module's concrete
SQLAlchemy adapter classes and wires them into that module's `Commands`/
`Queries` service. Each factory function takes a `UnitOfWork`/`ReadScope`
(from `app.shared.api` for FastAPI routes, or `app.shared.execution` for
everything else) and returns a fully-wired service object — callers never
construct a repository or adapter themselves.
"""

from __future__ import annotations

from app.combinations.adapters.sqlalchemy_combination_queries import (
    SqlAlchemyCombinationQueries,
)
from app.combinations.adapters.sqlalchemy_combination_repository import (
    SqlAlchemyCombinationRepository,
)
from app.combinations.commands import CombinationsCommands
from app.combinations.queries import CombinationsQueries
from app.generation.adapters.sqlalchemy_generation_job_queries import (
    SqlAlchemyGenerationJobQueries,
)
from app.generation.adapters.sqlalchemy_generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generation.commands import GenerationCommands
from app.generation.queries import GenerationQueries
from app.rules.adapters.sqlalchemy_rule_queries import SqlAlchemyRuleQueries
from app.rules.adapters.sqlalchemy_rule_repository import SqlAlchemyRuleRepository
from app.rules.commands import RulesCommands
from app.rules.queries import RulesQueries
from app.shared.database.port import ReadScope, UnitOfWork
from app.tables.adapters.sqlalchemy_decision_table_queries import (
    SqlAlchemyDecisionTableQueries,
)
from app.tables.adapters.sqlalchemy_decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)
from app.tables.commands import TablesCommands
from app.tables.queries import TablesQueries


def build_tables_commands(uow: UnitOfWork) -> TablesCommands:
    return TablesCommands(
        SqlAlchemyDecisionTableRepository(uow),
        SqlAlchemyGenerationJobRepository(uow),
        SqlAlchemyCombinationRepository(uow),
        SqlAlchemyRuleRepository(uow),
    )


def build_tables_queries(scope: ReadScope) -> TablesQueries:
    return TablesQueries(SqlAlchemyDecisionTableQueries(scope))


def build_rules_commands(uow: UnitOfWork) -> RulesCommands:
    return RulesCommands(
        SqlAlchemyDecisionTableRepository(uow),
        SqlAlchemyRuleRepository(uow),
        SqlAlchemyCombinationRepository(uow),
    )


def build_rules_queries(scope: ReadScope) -> RulesQueries:
    return RulesQueries(
        SqlAlchemyDecisionTableQueries(scope),
        SqlAlchemyRuleQueries(scope),
        SqlAlchemyCombinationQueries(scope),
    )


def build_combinations_commands(uow: UnitOfWork) -> CombinationsCommands:
    return CombinationsCommands(
        SqlAlchemyDecisionTableRepository(uow),
        SqlAlchemyCombinationRepository(uow),
    )


def build_combinations_queries(scope: ReadScope) -> CombinationsQueries:
    return CombinationsQueries(
        SqlAlchemyDecisionTableQueries(scope),
        SqlAlchemyCombinationQueries(scope),
    )


def build_generation_commands(uow: UnitOfWork) -> GenerationCommands:
    return GenerationCommands(
        SqlAlchemyDecisionTableRepository(uow),
        SqlAlchemyGenerationJobRepository(uow),
        SqlAlchemyCombinationRepository(uow),
    )


def build_generation_queries(scope: ReadScope) -> GenerationQueries:
    return GenerationQueries(SqlAlchemyGenerationJobQueries(scope))
