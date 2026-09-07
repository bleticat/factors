"""`Rule` — a saved partial factor->value assignment (unassigned factors mean
"any value") plus an output, applied as a set-based update over
`Combination` rows exactly like `BulkPatchCombinationsCommand` does, but kept
as its own record so it can be listed and re-applied later (see spec 005).
Deliberately not part of the `DecisionTable` aggregate, same rationale as
`Combination`.
"""

from __future__ import annotations

from collections.abc import Sequence
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
    factor_values: list[RuleAssignment] = field(default_factory=list)
    matched_count: int = 0
    applied_at: datetime | None = None


def _assignment_pairs(factor_values: Sequence[RuleAssignment]) -> frozenset[tuple[int, int]]:
    return frozenset((fv.factor_id, fv.factor_value_id) for fv in factor_values)


def is_at_least_as_general(
    candidate: Sequence[RuleAssignment], other: Sequence[RuleAssignment]
) -> bool:
    """True when `candidate`'s assignment is a subset of `other`'s (pairwise
    on `(factor_id, factor_value_id)`), i.e. every row `other` matches,
    `candidate` also matches — `candidate` is equally or more general than
    `other`. Equal assignments count as "at least as general" (neither
    refines the other). Used by `CreateRuleCommand` (spec 007) to reject a
    new rule that would be at least as general as an already-existing one;
    a new rule is only allowed to *refine* an existing one (be a strict
    superset of its assignment) or be incomparable with it."""
    return _assignment_pairs(candidate) <= _assignment_pairs(other)
