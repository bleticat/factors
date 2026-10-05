from fastapi import APIRouter, Depends, Request

from app.rules.api import schemas
from app.rules.use_cases import (
    CreateRuleRequest,
    DeleteRuleRequest,
    ListRuleOverlapsRequest,
    ListRulesRequest,
    ReapplyRulesRequest,
    ReorderRulesRequest,
    RulesUseCases,
    UpdateRuleRequest,
)
from app.shared.pagination import PageRequest

router = APIRouter()


def get_rules_use_cases(request: Request) -> RulesUseCases:
    return RulesUseCases(request.app.state.database)


@router.post("/{table_id}/rules", status_code=201)
async def create_rule(
    table_id: int,
    body: schemas.CreateRuleRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    response = await use_cases.create_rule(
        CreateRuleRequest(
            table_id=table_id,
            factor_values=tuple(body.factor_values),
            output=body.output,
            title=body.title,
        )
    )
    return response.rule


@router.get("/{table_id}/rules")
async def list_rules(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    response = await use_cases.list_rules(
        ListRulesRequest(
            table_id=table_id, page=PageRequest(limit=limit, offset=offset)
        )
    )
    return response.page


@router.get("/{table_id}/rules/overlaps")
async def list_rule_overlaps(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    response = await use_cases.list_rule_overlaps(
        ListRuleOverlapsRequest(
            table_id=table_id, page=PageRequest(limit=limit, offset=offset)
        )
    )
    return response.page


@router.patch("/{table_id}/rules/{rule_id}")
async def update_rule(
    table_id: int,
    rule_id: int,
    body: schemas.UpdateRuleRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    fields = body.model_fields_set
    response = await use_cases.update_rule(
        UpdateRuleRequest(
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
    )
    return response.rule


@router.delete("/{table_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    table_id: int, rule_id: int, use_cases: RulesUseCases = Depends(get_rules_use_cases)
) -> None:
    await use_cases.delete_rule(DeleteRuleRequest(table_id=table_id, rule_id=rule_id))


@router.post("/{table_id}/rules/reapply")
async def reapply_rules(
    table_id: int, use_cases: RulesUseCases = Depends(get_rules_use_cases)
):
    response = await use_cases.reapply_rules(ReapplyRulesRequest(table_id))
    return response


@router.post("/{table_id}/rules/reorder")
async def reorder_rules(
    table_id: int,
    body: schemas.ReorderRulesRequest,
    use_cases: RulesUseCases = Depends(get_rules_use_cases),
):
    response = await use_cases.reorder_rules(
        ReorderRulesRequest(
            table_id=table_id, ordered_rule_ids=tuple(body.ordered_rule_ids)
        )
    )
    return response
