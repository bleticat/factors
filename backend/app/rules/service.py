"""Internal helper logic `rules.commands` delegates to. Not part of the
module's public request/response surface."""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class RuleApplyRef:
    rule_id: int
    matched_count: int
    applied_at: datetime


async def apply_rule(
    combinations: CombinationRepository, rules: RuleRepository, rule: Rule
) -> RuleApplyRef:
    """Shared "apply a rule to the table's current combinations" logic, used
    by both `CreateRuleCommand` (apply once, immediately) and
    `ReapplyRulesCommand` (replay every rule after regeneration or on
    demand) — see spec 005. A rule's apply is exactly a
    `BulkPatchCombinationsCommand` with the rule's assignment as the filter
    and `status=possible`/`output=<rule.output>` as the patch."""
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
    return RuleApplyRef(rule_id=rule.id, matched_count=matched, applied_at=applied_at)
