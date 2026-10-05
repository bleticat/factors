from dataclasses import dataclass, field
from enum import StrEnum

from factors.shared.errors import ValidationError


class CombinationStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    POSSIBLE = "possible"
    IMPOSSIBLE = "impossible"


def parse_status(value: str) -> CombinationStatus:
    try:
        return CombinationStatus(value)
    except ValueError as exc:
        raise ValidationError(f"{value!r} is not a valid combination status") from exc


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
    if not value_counts:
        return 0
    total = 1
    for count in value_counts:
        if count == 0:
            return 0
        total *= count
    return total


def decompose_index(index: int, value_counts: list[int]) -> list[int]:
    picks = [0] * len(value_counts)
    remainder = index
    for i in range(len(value_counts) - 1, -1, -1):
        remainder, picks[i] = divmod(remainder, value_counts[i])
    return picks


def build_signature(factor_value_ids: list[int]) -> str:
    return "-".join(str(v) for v in factor_value_ids)
