"""`Rule` — a saved partial factor->value assignment (unassigned factors mean
"any value") plus an output, applied as a set-based update over
`Combination` rows exactly like `BulkPatchCombinationsCommand` does, but kept
as its own record so it can be listed and re-applied later (see spec 005).
Deliberately not part of the `DecisionTable` aggregate, same rationale as
`Combination`.
"""

from __future__ import annotations

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
