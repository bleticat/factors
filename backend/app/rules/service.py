from datetime import UTC, datetime

from app.combinations.entities import CombinationStatus
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    CombinationRepository,
    FactorValueAssignment,
)
from app.rules.entities import Rule
from app.rules.ports.rule_repository import RuleRepository


async def apply_rule(
    combinations: CombinationRepository, rules: RuleRepository, rule: Rule
) -> Rule:
    assert rule.id is not None
    filter_ = CombinationFilter(
        factor_values=tuple(
            FactorValueAssignment(
                factor_id=a.factor_id, factor_value_id=a.factor_value_id
            )
            for a in rule.factor_values
        )
    )
    patch = CombinationPatch(
        status=CombinationStatus.POSSIBLE, output=rule.output, output_set=True
    )
    matched, _ = await combinations.bulk_update_status(
        rule.decision_table_id, filter_, patch
    )

    applied_at = datetime.now(UTC).replace(tzinfo=None)
    await rules.record_apply(rule.id, matched, applied_at)
    rule.matched_count = matched
    rule.applied_at = applied_at
    return rule
