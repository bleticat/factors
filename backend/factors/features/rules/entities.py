from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RuleAssignment:
    factor_id: int
    factor_value_id: int


@dataclass
class Rule:
    id: int | None
    decision_table_id: int
    output: str
    title: str | None = None
    order_index: int = 0
    factor_values: list[RuleAssignment] = field(default_factory=list)
    matched_count: int = 0
    applied_at: datetime | None = None
    created_at: datetime | None = None
    # How many of this rule's own matched rows are shadowed by a rule later
    # in apply order (spec 009) — i.e. currently show a *different* rule's
    # output. Computed and attached by `RulesUseCases.list_rules`, the one
    # place that needs it; every other path leaves it at the default,
    # exactly like `matched_count`/`applied_at` are only meaningful once
    # `apply_rule` has attached them.
    shadowed_count: int = 0
