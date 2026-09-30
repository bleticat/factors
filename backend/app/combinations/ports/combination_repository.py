from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.combinations.entities import Combination, CombinationStatus


@dataclass(frozen=True)
class FactorValueAssignment:
    factor_id: int
    factor_value_id: int


@dataclass(frozen=True)
class CombinationFilter:
    status: CombinationStatus | None = None
    factor_values: tuple[FactorValueAssignment, ...] = ()


@dataclass(frozen=True)
class CombinationPatch:
    status: CombinationStatus | None = None
    output: str | None = None
    output_set: bool = False
    impossible_reason: str | None = None
    impossible_reason_set: bool = False


class CombinationRepository(ABC):
    """Write-side port for `Combination`/`CombinationValue`. Deliberately
    NOT a whole-aggregate load/mutate/save port at this row count — see the
    plan's "Domain model / aggregates" section. `bulk_insert` and
    `bulk_update_status` are set-based SQL operations; `get`/`save` support
    the single-row edit path."""

    @abstractmethod
    async def bulk_insert(self, combinations: list[Combination]) -> None:
        """Insert a batch of newly-generated combinations in one set-based
        operation."""

    @abstractmethod
    async def get(self, table_id: int, combination_id: int) -> Combination | None:
        """Return one combination, or None if it doesn't exist on this table."""

    @abstractmethod
    async def save(self, combination: Combination) -> None:
        """Persist status/output/impossible_reason for one already-existing
        combination."""

    @abstractmethod
    async def bulk_update_status(
        self, table_id: int, filter_: CombinationFilter, patch: CombinationPatch
    ) -> tuple[int, int]:
        """Apply `patch` to every combination in `table_id` matching
        `filter_` in one set-based UPDATE. Returns (matched_count,
        updated_count) — the two are equal in v1 since there's no
        concurrent-modification detection, but kept distinct in the
        signature for that future case."""

    @abstractmethod
    async def delete_all_for_table(self, table_id: int) -> None:
        """Used both by regeneration (delete-and-recreate) and by factor/
        value deletion (invalidates existing combinations' signatures)."""
