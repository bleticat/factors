"""Thin HTTP boundary: parse input, submit a typed request to the mediator,
serialize the result (ADR 007). The only exception is `request_generation`,
which additionally schedules the background batch loop — that loop is
itself a boundary, not a handler (see `background/generation_worker.py`)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.config import settings
from app.decision_tables.api import schemas
from app.decision_tables.background.generation_worker import run_generation_job
from app.decision_tables.commands.add_factor import AddFactorCommand
from app.decision_tables.commands.add_factor_value import AddFactorValueCommand
from app.decision_tables.commands.bulk_patch_combinations import (
    BulkFilterInput,
    BulkPatchCombinationsCommand,
    BulkPatchInput,
)
from app.decision_tables.commands.cancel_generation_job import (
    CancelGenerationJobCommand,
)
from app.decision_tables.commands.create_decision_table import (
    CreateDecisionTableCommand,
)
from app.decision_tables.commands.create_rule import CreateRuleCommand
from app.decision_tables.commands.delete_decision_table import (
    DeleteDecisionTableCommand,
)
from app.decision_tables.commands.delete_factor import DeleteFactorCommand
from app.decision_tables.commands.delete_factor_value import DeleteFactorValueCommand
from app.decision_tables.commands.delete_rule import DeleteRuleCommand
from app.decision_tables.commands.patch_combination import PatchCombinationCommand
from app.decision_tables.commands.reapply_rules import ReapplyRulesCommand
from app.decision_tables.commands.reorder_rules import ReorderRulesCommand
from app.decision_tables.commands.request_generation import RequestGenerationCommand
from app.decision_tables.commands.update_decision_table import (
    UpdateDecisionTableCommand,
)
from app.decision_tables.commands.update_factor import UpdateFactorCommand
from app.decision_tables.commands.update_factor_value import UpdateFactorValueCommand
from app.decision_tables.commands.update_rule import UpdateRuleCommand
from app.decision_tables.queries.evaluate_combinations import EvaluateCombinationsQuery
from app.decision_tables.queries.get_decision_table import GetDecisionTableQuery
from app.decision_tables.queries.get_generation_job import GetGenerationJobQuery
from app.decision_tables.queries.list_combinations import ListCombinationsQuery
from app.decision_tables.queries.list_decision_tables import ListDecisionTablesQuery
from app.decision_tables.queries.list_factors import ListFactorsQuery
from app.decision_tables.queries.list_rule_overlaps import ListRuleOverlapsQuery
from app.decision_tables.queries.list_rules import ListRulesQuery
from app.shared.mediator.mediator import Mediator
from app.shared.pagination import PageRequest

router = APIRouter()


def get_mediator(request: Request) -> Mediator:
    return request.app.state.mediator


@router.post("", status_code=201)
async def create_decision_table(
    body: schemas.CreateDecisionTableRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(CreateDecisionTableCommand(name=body.name, description=body.description))


@router.get("")
async def list_decision_tables(
    limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(ListDecisionTablesQuery(page=PageRequest(limit=limit, offset=offset)))


@router.get("/{table_id}")
async def get_decision_table(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(GetDecisionTableQuery(table_id=table_id))


@router.patch("/{table_id}")
async def update_decision_table(
    table_id: int,
    body: schemas.UpdateDecisionTableRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        UpdateDecisionTableCommand(
            table_id=table_id,
            name=body.name,
            description=body.description,
            description_set="description" in fields,
        )
    )


@router.delete("/{table_id}", status_code=204)
async def delete_decision_table(table_id: int, mediator: Mediator = Depends(get_mediator)) -> None:
    await mediator.execute(DeleteDecisionTableCommand(table_id=table_id))


@router.post("/{table_id}/factors", status_code=201)
async def add_factor(
    table_id: int, body: schemas.AddFactorRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(AddFactorCommand(table_id=table_id, name=body.name))


@router.get("/{table_id}/factors")
async def list_factors(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(ListFactorsQuery(table_id=table_id))


@router.patch("/{table_id}/factors/{factor_id}")
async def update_factor(
    table_id: int,
    factor_id: int,
    body: schemas.UpdateFactorRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        UpdateFactorCommand(
            table_id=table_id, factor_id=factor_id, name=body.name, order_index=body.order_index
        )
    )


@router.delete("/{table_id}/factors/{factor_id}", status_code=204)
async def delete_factor(
    table_id: int, factor_id: int, mediator: Mediator = Depends(get_mediator)
) -> None:
    await mediator.execute(DeleteFactorCommand(table_id=table_id, factor_id=factor_id))


@router.post("/{table_id}/factors/{factor_id}/values", status_code=201)
async def add_factor_value(
    table_id: int,
    factor_id: int,
    body: schemas.AddFactorValueRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        AddFactorValueCommand(table_id=table_id, factor_id=factor_id, value=body.value)
    )


@router.patch("/{table_id}/factors/{factor_id}/values/{value_id}")
async def update_factor_value(
    table_id: int,
    factor_id: int,
    value_id: int,
    body: schemas.UpdateFactorValueRequest,
    mediator: Mediator = Depends(get_mediator),
):
    return await mediator.execute(
        UpdateFactorValueCommand(
            table_id=table_id,
            factor_id=factor_id,
            value_id=value_id,
            value=body.value,
            order_index=body.order_index,
        )
    )


@router.delete("/{table_id}/factors/{factor_id}/values/{value_id}", status_code=204)
async def delete_factor_value(
    table_id: int, factor_id: int, value_id: int, mediator: Mediator = Depends(get_mediator)
) -> None:
    await mediator.execute(
        DeleteFactorValueCommand(table_id=table_id, factor_id=factor_id, value_id=value_id)
    )


@router.post("/{table_id}/generation-jobs", status_code=202)
async def request_generation(
    table_id: int, background_tasks: BackgroundTasks, mediator: Mediator = Depends(get_mediator)
):
    job = await mediator.execute(RequestGenerationCommand(table_id=table_id))
    background_tasks.add_task(
        run_generation_job,
        mediator=mediator,
        job_id=job.id,
        batch_size=settings.generation_batch_size,
    )
    return job


@router.get("/{table_id}/generation-jobs/{job_id}")
async def get_generation_job(
    table_id: int, job_id: int, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(GetGenerationJobQuery(job_id=job_id))


@router.post("/{table_id}/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    table_id: int, job_id: int, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(CancelGenerationJobCommand(job_id=job_id))


@router.get("/{table_id}/combinations")
async def list_combinations(
    table_id: int,
    status: str | None = None,
    fv: list[str] = Query(default_factory=list),
    limit: int = 50,
    offset: int = 0,
    mediator: Mediator = Depends(get_mediator),
):
    """`fv` is a repeatable `factor_id:factor_value_id` pair, e.g.
    `?fv=3:9&fv=5:14` — the same AND-ed filter shape bulk-patch uses."""
    return await mediator.execute(
        ListCombinationsQuery(
            table_id=table_id,
            status=status,
            factor_values=tuple(_parse_factor_value_pair(pair) for pair in fv),
            page=PageRequest(limit=limit, offset=offset),
        )
    )


def _parse_factor_value_pair(pair: str) -> tuple[int, int]:
    factor_id_str, _, value_id_str = pair.partition(":")
    return int(factor_id_str), int(value_id_str)


@router.patch("/{table_id}/combinations/{combination_id}")
async def patch_combination(
    table_id: int,
    combination_id: int,
    body: schemas.PatchCombinationRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        PatchCombinationCommand(
            table_id=table_id,
            combination_id=combination_id,
            status=body.status,
            output=body.output,
            output_set="output" in fields,
            impossible_reason=body.impossible_reason,
            impossible_reason_set="impossible_reason" in fields,
        )
    )


@router.post("/{table_id}/combinations/bulk-patch")
async def bulk_patch_combinations(
    table_id: int,
    body: schemas.BulkPatchCombinationsRequest,
    mediator: Mediator = Depends(get_mediator),
):
    patch_fields = body.patch.model_fields_set
    return await mediator.execute(
        BulkPatchCombinationsCommand(
            table_id=table_id,
            filter=BulkFilterInput(
                status=body.filter.status,
                factor_values=tuple(body.filter.factor_values),
            ),
            patch=BulkPatchInput(
                status=body.patch.status,
                output=body.patch.output,
                output_set="output" in patch_fields,
                impossible_reason=body.patch.impossible_reason,
                impossible_reason_set="impossible_reason" in patch_fields,
            ),
        )
    )


@router.post("/{table_id}/evaluate")
async def evaluate(
    table_id: int, body: schemas.EvaluateRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        EvaluateCombinationsQuery(
            table_id=table_id,
            assignment=tuple(body.assignment),
            page=PageRequest(limit=body.limit, offset=body.offset),
        )
    )


@router.post("/{table_id}/rules", status_code=201)
async def create_rule(
    table_id: int, body: schemas.CreateRuleRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        CreateRuleCommand(
            table_id=table_id,
            factor_values=tuple(body.factor_values),
            output=body.output,
            title=body.title,
        )
    )


@router.get("/{table_id}/rules")
async def list_rules(
    table_id: int, limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ListRulesQuery(table_id=table_id, page=PageRequest(limit=limit, offset=offset))
    )


@router.get("/{table_id}/rules/overlaps")
async def list_rule_overlaps(
    table_id: int, limit: int = 50, offset: int = 0, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ListRuleOverlapsQuery(table_id=table_id, page=PageRequest(limit=limit, offset=offset))
    )


@router.patch("/{table_id}/rules/{rule_id}")
async def update_rule(
    table_id: int,
    rule_id: int,
    body: schemas.UpdateRuleRequest,
    mediator: Mediator = Depends(get_mediator),
):
    fields = body.model_fields_set
    return await mediator.execute(
        UpdateRuleCommand(
            table_id=table_id,
            rule_id=rule_id,
            output=body.output,
            title=body.title,
            title_set="title" in fields,
            factor_values=tuple(body.factor_values) if body.factor_values is not None else None,
            factor_values_set="factor_values" in fields,
        )
    )


@router.delete("/{table_id}/rules/{rule_id}", status_code=204)
async def delete_rule(table_id: int, rule_id: int, mediator: Mediator = Depends(get_mediator)) -> None:
    await mediator.execute(DeleteRuleCommand(table_id=table_id, rule_id=rule_id))


@router.post("/{table_id}/rules/reapply")
async def reapply_rules(table_id: int, mediator: Mediator = Depends(get_mediator)):
    return await mediator.execute(ReapplyRulesCommand(table_id=table_id))


@router.post("/{table_id}/rules/reorder")
async def reorder_rules(
    table_id: int, body: schemas.ReorderRulesRequest, mediator: Mediator = Depends(get_mediator)
):
    return await mediator.execute(
        ReorderRulesCommand(table_id=table_id, ordered_rule_ids=tuple(body.ordered_rule_ids))
    )
