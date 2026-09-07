"""The composition root (ADR 007): explicit, typed `dict[type, factory]`
wiring for every command and query the `decision_tables` context exposes.
No reflection, no DI container, no string-based routing — each request type
maps to exactly one line here, built once at app startup."""

from __future__ import annotations

from app.decision_tables.adapters.sqlalchemy_combination_queries import (
    SqlAlchemyCombinationQueries,
)
from app.decision_tables.adapters.sqlalchemy_combination_repository import (
    SqlAlchemyCombinationRepository,
)
from app.decision_tables.adapters.sqlalchemy_decision_table_queries import (
    SqlAlchemyDecisionTableQueries,
)
from app.decision_tables.adapters.sqlalchemy_decision_table_repository import (
    SqlAlchemyDecisionTableRepository,
)
from app.decision_tables.adapters.sqlalchemy_generation_job_queries import (
    SqlAlchemyGenerationJobQueries,
)
from app.decision_tables.adapters.sqlalchemy_generation_job_repository import (
    SqlAlchemyGenerationJobRepository,
)
from app.decision_tables.commands.add_factor import AddFactorCommand, AddFactorHandler
from app.decision_tables.commands.add_factor_value import (
    AddFactorValueCommand,
    AddFactorValueHandler,
)
from app.decision_tables.commands.bulk_patch_combinations import (
    BulkPatchCombinationsCommand,
    BulkPatchCombinationsHandler,
)
from app.decision_tables.commands.cancel_generation_job import (
    CancelGenerationJobCommand,
    CancelGenerationJobHandler,
)
from app.decision_tables.commands.create_decision_table import (
    CreateDecisionTableCommand,
    CreateDecisionTableHandler,
)
from app.decision_tables.commands.delete_decision_table import (
    DeleteDecisionTableCommand,
    DeleteDecisionTableHandler,
)
from app.decision_tables.commands.delete_factor import (
    DeleteFactorCommand,
    DeleteFactorHandler,
)
from app.decision_tables.commands.delete_factor_value import (
    DeleteFactorValueCommand,
    DeleteFactorValueHandler,
)
from app.decision_tables.commands.generate_combinations_batch import (
    GenerateCombinationsBatchCommand,
    GenerateCombinationsBatchHandler,
)
from app.decision_tables.commands.mark_generation_job_failed import (
    MarkGenerationJobFailedCommand,
    MarkGenerationJobFailedHandler,
)
from app.decision_tables.commands.mark_stale_generation_jobs_failed import (
    MarkStaleGenerationJobsFailedCommand,
    MarkStaleGenerationJobsFailedHandler,
)
from app.decision_tables.commands.patch_combination import (
    PatchCombinationCommand,
    PatchCombinationHandler,
)
from app.decision_tables.commands.request_generation import (
    RequestGenerationCommand,
    RequestGenerationHandler,
)
from app.decision_tables.commands.update_decision_table import (
    UpdateDecisionTableCommand,
    UpdateDecisionTableHandler,
)
from app.decision_tables.commands.update_factor import (
    UpdateFactorCommand,
    UpdateFactorHandler,
)
from app.decision_tables.commands.update_factor_value import (
    UpdateFactorValueCommand,
    UpdateFactorValueHandler,
)
from app.decision_tables.queries.evaluate_combinations import (
    EvaluateCombinationsHandler,
    EvaluateCombinationsQuery,
)
from app.decision_tables.queries.get_decision_table import (
    GetDecisionTableHandler,
    GetDecisionTableQuery,
)
from app.decision_tables.queries.get_generation_job import (
    GetGenerationJobHandler,
    GetGenerationJobQuery,
)
from app.decision_tables.queries.list_combinations import (
    ListCombinationsHandler,
    ListCombinationsQuery,
)
from app.decision_tables.queries.list_decision_tables import (
    ListDecisionTablesHandler,
    ListDecisionTablesQuery,
)
from app.decision_tables.queries.list_factors import (
    ListFactorsHandler,
    ListFactorsQuery,
)
from app.decision_tables.queries.list_stale_running_generation_jobs import (
    ListStaleRunningGenerationJobsHandler,
    ListStaleRunningGenerationJobsQuery,
)
from app.shared.database.port import Database
from app.shared.mediator.mediator import Mediator


def build_mediator(database: Database, *, max_combinations: int) -> Mediator:
    command_registry = {
        CreateDecisionTableCommand: lambda uow: CreateDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow.session)
        ),
        UpdateDecisionTableCommand: lambda uow: UpdateDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow.session)
        ),
        DeleteDecisionTableCommand: lambda uow: DeleteDecisionTableHandler(
            SqlAlchemyDecisionTableRepository(uow.session)
        ),
        AddFactorCommand: lambda uow: AddFactorHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
        ),
        UpdateFactorCommand: lambda uow: UpdateFactorHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
        ),
        DeleteFactorCommand: lambda uow: DeleteFactorHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
            SqlAlchemyCombinationRepository(uow.session),
        ),
        AddFactorValueCommand: lambda uow: AddFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
        ),
        UpdateFactorValueCommand: lambda uow: UpdateFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
        ),
        DeleteFactorValueCommand: lambda uow: DeleteFactorValueHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
            SqlAlchemyCombinationRepository(uow.session),
        ),
        RequestGenerationCommand: lambda uow: RequestGenerationHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyGenerationJobRepository(uow.session),
            SqlAlchemyCombinationRepository(uow.session),
            max_combinations,
        ),
        GenerateCombinationsBatchCommand: lambda uow: GenerateCombinationsBatchHandler(
            SqlAlchemyGenerationJobRepository(uow.session),
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyCombinationRepository(uow.session),
        ),
        MarkGenerationJobFailedCommand: lambda uow: MarkGenerationJobFailedHandler(
            SqlAlchemyGenerationJobRepository(uow.session)
        ),
        MarkStaleGenerationJobsFailedCommand: lambda uow: MarkStaleGenerationJobsFailedHandler(
            SqlAlchemyGenerationJobRepository(uow.session)
        ),
        CancelGenerationJobCommand: lambda uow: CancelGenerationJobHandler(
            SqlAlchemyGenerationJobRepository(uow.session)
        ),
        PatchCombinationCommand: lambda uow: PatchCombinationHandler(
            SqlAlchemyCombinationRepository(uow.session)
        ),
        BulkPatchCombinationsCommand: lambda uow: BulkPatchCombinationsHandler(
            SqlAlchemyDecisionTableRepository(uow.session),
            SqlAlchemyCombinationRepository(uow.session),
        ),
    }

    query_registry = {
        GetDecisionTableQuery: lambda scope: GetDecisionTableHandler(
            SqlAlchemyDecisionTableQueries(scope.session)
        ),
        ListDecisionTablesQuery: lambda scope: ListDecisionTablesHandler(
            SqlAlchemyDecisionTableQueries(scope.session)
        ),
        ListFactorsQuery: lambda scope: ListFactorsHandler(
            SqlAlchemyDecisionTableQueries(scope.session)
        ),
        GetGenerationJobQuery: lambda scope: GetGenerationJobHandler(
            SqlAlchemyGenerationJobQueries(scope.session)
        ),
        ListStaleRunningGenerationJobsQuery: lambda scope: ListStaleRunningGenerationJobsHandler(
            SqlAlchemyGenerationJobQueries(scope.session)
        ),
        ListCombinationsQuery: lambda scope: ListCombinationsHandler(
            SqlAlchemyDecisionTableQueries(scope.session),
            SqlAlchemyCombinationQueries(scope.session),
        ),
        EvaluateCombinationsQuery: lambda scope: EvaluateCombinationsHandler(
            SqlAlchemyDecisionTableQueries(scope.session),
            SqlAlchemyCombinationQueries(scope.session),
        ),
    }

    return Mediator(database, command_registry, query_registry)
