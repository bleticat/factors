"""Thin HTTP boundary: parse input, call the module's use cases, serialize
the result."""

from fastapi import APIRouter, Depends, Request

from app.rules.api import schemas
from app.rules.use_cases import RulesUseCases
from app.shared.pagination import PageRequest

router = APIRouter()


def get_rules_use_cases(request: Request) -> RulesUseCases:
    """FastAPI dependency: build a `RulesUseCases` for the current request."""
    return RulesUseCases(request.app.state.database)


@router.post("/{table_id}/rules", status_code=201)
async def create_rule(
    table_id: int,
    body: schemas.CreateRuleRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    """Create a new rule and immediately apply it to the table's current
    combinations."""
    return await use_cases.create_rule(
        table_id=table_id,
        factor_values=tuple(body.factor_values),
        output=body.output,
        title=body.title,
    )


@router.get("/{table_id}/rules")
async def list_rules(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    """List a decision table's rules, each tagged with its shadowed-match count."""
    return await use_cases.list_rules(
        table_id=table_id, page=PageRequest(limit=limit, offset=offset)
    )


@router.get("/{table_id}/rules/overlaps")
async def list_rule_overlaps(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    """List combinations matched by 2+ of the table's current rules."""
    return await use_cases.list_rule_overlaps(
        table_id=table_id, page=PageRequest(limit=limit, offset=offset)
    )


@router.patch("/{table_id}/rules/{rule_id}")
async def update_rule(
    table_id: int,
    rule_id: int,
    body: schemas.UpdateRuleRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    """Update a rule's output, title, and/or assignment in place."""
    fields = body.model_fields_set
    return await use_cases.update_rule(
        table_id=table_id,
        rule_id=rule_id,
        output=body.output,
        title=body.title,
        title_set="title" in fields,
        factor_values=tuple(body.factor_values)
        if body.factor_values is not None
        else None,
        factor_values_set="factor_values" in fields,
    )


@router.delete("/{table_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    table_id: int, rule_id: int, use_cases: RulesUseCases = Depends(get_rules_use_cases)
) -> None:
    """Delete a rule."""
    await use_cases.delete_rule(table_id=table_id, rule_id=rule_id)


@router.post("/{table_id}/rules/reapply")
async def reapply_rules(
    table_id: int, use_cases: RulesUseCases = Depends(get_rules_use_cases)
):
    """Replay every rule for a table against its current combinations, in order."""
    return await use_cases.reapply_rules(table_id)


@router.post("/{table_id}/rules/reorder")
async def reorder_rules(
    table_id: int,
    body: schemas.ReorderRulesRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    """Persist a complete new rule order and immediately replay every rule
    in that order."""
    return await use_cases.reorder_rules(
        table_id=table_id, ordered_rule_ids=tuple(body.ordered_rule_ids)
    )
