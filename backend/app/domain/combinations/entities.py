"""`Combination`/`CombinationValue` — deliberately not part of the
`DecisionTable` aggregate (can be tens of thousands of rows); see the plan's
"Domain model / aggregates" section for why bulk operations on these are a
set-based repository exception rather than load/mutate/save.

Also home to the mixed-radix cursor <-> per-factor-value-index arithmetic
used by generation batching, since it's pure domain logic independent of
persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.combinations.errors import InvalidCombinationStatusError


class CombinationStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    POSSIBLE = "possible"
    IMPOSSIBLE = "impossible"


def parse_status(value: str) -> CombinationStatus:
    try:
        return CombinationStatus(value)
    except ValueError as exc:
        raise InvalidCombinationStatusError(value) from exc


@dataclass
class CombinationValue:
    factor_id: int
    factor_value_id: int


@dataclass
class Combination:
    id: int | None
    decision_table_id: int
    generation_job_id: int
    signature: str
    status: CombinationStatus = CombinationStatus.UNREVIEWED
    output: str | None = None
    impossible_reason: str | None = None
    values: list[CombinationValue] = field(default_factory=list)


def total_combinations(value_counts: list[int]) -> int:
    """Product of each factor's value count. 0 if any factor has 0 values or
    there are no factors."""
    if not value_counts:
        return 0
    total = 1
    for count in value_counts:
        if count == 0:
            return 0
        total *= count
    return total


def decompose_index(index: int, value_counts: list[int]) -> list[int]:
    """Decompose a flat combination index into a per-factor value-pick index,
    matching `itertools.product(*[range(n) for n in value_counts])` order
    exactly: the last factor varies fastest (least-significant digit),
    computed via mixed-radix `divmod` rather than re-walking `itertools`
    from 0 each call, since the latter is quadratic as the cursor grows.
    """
    picks = [0] * len(value_counts)
    remainder = index
    for i in range(len(value_counts) - 1, -1, -1):
        remainder, picks[i] = divmod(remainder, value_counts[i])
    return picks


def build_signature(factor_value_ids: list[int]) -> str:
    """Deterministic signature for a combination's factor-value picks, in
    factor order. Used for the unique(decision_table_id, signature)
    constraint and as a low-cost hook for future idempotent regeneration.
    """
    return "-".join(str(v) for v in factor_value_ids)
