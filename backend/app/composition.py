"""The composition root (ADR 007): explicit, typed `dict[type, factory]`
wiring for every command and query the app exposes, across the `tables`,
`rules`, `combinations`, and `generation` modules. No reflection, no DI
container, no string-based routing — each request type maps to exactly one
line here, built once at app startup."""

from __future__ import annotations

from app.combinations.adapters.sqlalchemy_combination_queries import (
    SqlAlchemyCombinationQueries,
)
from app.combinations.adapters.sqlalchemy_combination_repository import (
    SqlAlchemyCombinationRepository,
)
from app.combinations.commands import (
    BulkPatchCombinationsCommand,
    BulkPatchCombinationsHandler,
    PatchCombinationCommand,
    PatchCombinationHandler,
)
from app.combinations.queries import (
    EvaluateCombinationsHandler,
    EvaluateCombinationsQuery,
    ListCombinationsHandler,
    ListCombinationsQuery,
)
from app.generation.adapters.sqlalchemy_generation_job_queries import (
    SqlAlchemyGenerationJobQueries,
)
from app.generation.adapters.sqlalchemy_generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.generation.commands import (
    CancelGenerationJobCommand,
    CancelGenerationJobHandler,
    GenerateCombinationsBatchCommand,
    GenerateCombinationsBatchHandler,
    MarkGenerationJobFailedCommand,
    MarkGenerationJobFailedHandler,
    MarkStaleGenerationJobsFailedCommand,
    MarkStaleGenerationJobsFailedHandler,
    RequestGenerationCommand,
    RequestGenerationHandler,
)
from app.generation.queries import (
    GetGenerationJobHandler,
    GetGenerationJobQuery,
    ListStaleRunningGenerationJobsHandler,
    ListStaleRunningGenerationJobsQuery,
)
from app.rules.adapters.sqlalchemy_rule_queries import SqlAlchemyRuleQueries
from app.rules.adapters.sqlalchemy_rule_repository import SqlAlchemyRuleRepository
from app.rules.commands import (
    CreateRuleCommand,
    CreateRuleHandler,
    DeleteRuleCommand,
    DeleteRuleHandler,
    ReapplyRulesCommand,
    ReapplyRulesHandler,
    ReorderRulesCommand,
    ReorderRulesHandler,
    UpdateRuleCommand,
    UpdateRuleHandler,
)
from app.rules.queries import (
    ListRuleOverlapsHandler,
    ListRuleOverlapsQuery,
    ListRulesHandler,
    ListRulesQuery,
)
from app.shared.database.port import Database
from app.shared.mediator.mediator import Mediator
from app.tables.adapters.sqlalchemy_decision_table_queries import (
    SqlAlchemyDecisionTableQueries,
)
from app.tables.adapters.sqlalchemy_decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)
from app.tables.commands import (
    AddFactorCommand,
    AddFactorHandler,
    AddFactorValueCommand,
    AddFactorValueHandler,
    CreateDecisionTableCommand,
    CreateDecisionTableHandler,
    DeleteDecisionTableCommand,
    DeleteDecisionTableHandler,
    DeleteFactorCommand,
    DeleteFactorHandler,
    DeleteFactorValueCommand,
    DeleteFactorValueHandler,
    UpdateDecisionTableCommand,
    UpdateDecisionTableHandler,
    UpdateFactorCommand,
    UpdateFactorHandler,
    UpdateFactorValueCommand,
    UpdateFactorValueHandler,
)
from app.tables.queries import (
    GetDecisionTableHandler,
    GetDecisionTableQuery,
    ListDecisionTablesHandler,
    ListDecisionTablesQuery,
    ListFactorsHandler,
    ListFactorsQuery,
)


def build_mediator(database: Database, *, max_combinations: int) -> Mediator:
    command_registry = {
        CreateDecisionTableCommand: lambda uow: CreateDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow)
        ),
        UpdateDecisionTableCommand: lambda uow: UpdateDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow)
        ),
        DeleteDecisionTableCommand: lambda uow: DeleteDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow)
        ),
        AddFactorCommand: lambda uow: AddFactorHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
        ),
        UpdateFactorCommand: lambda uow: UpdateFactorHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
        ),
        DeleteFactorCommand: lambda uow: DeleteFactorHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
            SqlAlchemyCombinationRepository(uow),
            SqlAlchemyRuleRepository(uow),
        ),
        AddFactorValueCommand: lambda uow: AddFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
        ),
        UpdateFactorValueCommand: lambda uow: UpdateFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
        ),
        DeleteFactorValueCommand: lambda uow: DeleteFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
            SqlAlchemyCombinationRepository(uow),
            SqlAlchemyRuleRepository(uow),
        ),
        RequestGenerationCommand: lambda uow: RequestGenerationHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyGenerationJobRepository(uow),
            SqlAlchemyCombinationRepository(uow),
            max_combinations,
        ),
        GenerateCombinationsBatchCommand: lambda uow: GenerateCombinationsBatchHandler(
            SqlAlchemyGenerationJobRepository(uow),
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
        MarkGenerationJobFailedCommand: lambda uow: MarkGenerationJobFailedHandler(
            SqlAlchemyGenerationJobRepository(uow)
        ),
        MarkStaleGenerationJobsFailedCommand: lambda uow: MarkStaleGenerationJobsFailedHandler(
            SqlAlchemyGenerationJobRepository(uow)
        ),
        CancelGenerationJobCommand: lambda uow: CancelGenerationJobHandler(
            SqlAlchemyGenerationJobRepository(uow)
        ),
        PatchCombinationCommand: lambda uow: PatchCombinationHandler(
            SqlAlchemyCombinationRepository(uow)
        ),
        BulkPatchCombinationsCommand: lambda uow: BulkPatchCombinationsHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
        CreateRuleCommand: lambda uow: CreateRuleHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyRuleRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
        UpdateRuleCommand: lambda uow: UpdateRuleHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyRuleRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
        DeleteRuleCommand: lambda uow: DeleteRuleHandler(SqlAlchemyRuleRepository(uow)),
        ReapplyRulesCommand: lambda uow: ReapplyRulesHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyRuleRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
        ReorderRulesCommand: lambda uow: ReorderRulesHandler(
            SqlAlchemyDecisionTableRepository(uow),
            SqlAlchemyRuleRepository(uow),
            SqlAlchemyCombinationRepository(uow),
        ),
    }

    query_registry = {
        GetDecisionTableQuery: lambda scope: GetDecisionTableHandler(
            SqlAlchemyDecisionTableQueries(scope)
        ),
        ListDecisionTablesQuery: lambda scope: ListDecisionTablesHandler(
            SqlAlchemyDecisionTableQueries(scope)
        ),
        ListFactorsQuery: lambda scope: ListFactorsHandler(
            SqlAlchemyDecisionTableQueries(scope)
        ),
        GetGenerationJobQuery: lambda scope: GetGenerationJobHandler(
            SqlAlchemyGenerationJobQueries(scope)
        ),
        ListStaleRunningGenerationJobsQuery: lambda scope: ListStaleRunningGenerationJobsHandler(
            SqlAlchemyGenerationJobQueries(scope)
        ),
        ListCombinationsQuery: lambda scope: ListCombinationsHandler(
            SqlAlchemyDecisionTableQueries(scope),
            SqlAlchemyCombinationQueries(scope),
        ),
        EvaluateCombinationsQuery: lambda scope: EvaluateCombinationsHandler(
            SqlAlchemyDecisionTableQueries(scope),
            SqlAlchemyCombinationQueries(scope),
        ),
        ListRulesQuery: lambda scope: ListRulesHandler(
            SqlAlchemyDecisionTableQueries(scope),
            SqlAlchemyRuleQueries(scope),
            SqlAlchemyCombinationQueries(scope),
        ),
        ListRuleOverlapsQuery: lambda scope: ListRuleOverlapsHandler(
            SqlAlchemyDecisionTableQueries(scope),
            SqlAlchemyRuleQueries(scope),
            SqlAlchemyCombinationQueries(scope),
        ),
    }

    return Mediator(database, command_registry, query_registry)
