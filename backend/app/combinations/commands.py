"""Write-side use cases for the `combinations` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.combinations.entities import parse_status
from app.combinations.errors import CombinationNotFoundError
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    CombinationRepository,
    FactorValueAssignment,
)
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_repository import DecisionTableRepository


@dataclass(frozen=True)
class CombinationRef:
    id: int
    status: str
    output: str | None
    impossible_reason: str | None


@dataclass(frozen=True)
class BulkPatchResult:
    matched_count: int
    updated_count: int


@dataclass(frozen=True)
class BulkFilterInput:
    status: str | None = None
    factor_values: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class BulkPatchInput:
    status: str | None = None
    output: str | None = None
    output_set: bool = False
    impossible_reason: str | None = None
    impossible_reason_set: bool = False


class CombinationsCommands:
    """The `combinations` module's write-side use cases. Built per call by
    `app.composition.build_combinations_commands`."""

    def __init__(
        self, tables: DecisionTableRepository, combinations: CombinationRepository
    ) -> None:
        self._tables = tables
        self._combinations = combinations

    async def patch_combination(
        self,
        table_id: int,
        combination_id: int,
        status: str | None = None,
        output: str | None = None,
        output_set: bool = False,
        impossible_reason: str | None = None,
        impossible_reason_set: bool = False,
    ) -> CombinationRef:
        combination = await self._combinations.get(table_id, combination_id)
        if combination is None:
            raise CombinationNotFoundError(combination_id)

        if status is not None:
            combination.status = parse_status(status)
        if output_set:
            combination.output = output
        if impossible_reason_set:
            combination.impossible_reason = impossible_reason

        await self._combinations.save(combination)
        assert combination.id is not None
        return CombinationRef(
            id=combination.id,
            status=str(combination.status),
            output=combination.output,
            impossible_reason=combination.impossible_reason,
        )

    async def bulk_patch_combinations(
        self,
        table_id: int,
        filter: BulkFilterInput = BulkFilterInput(),
        patch: BulkPatchInput = BulkPatchInput(),
    ) -> BulkPatchResult:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        table.validate_factor_value_pairs(list(filter.factor_values))

        filter_ = CombinationFilter(
            status=parse_status(filter.status) if filter.status is not None else None,
            factor_values=tuple(
                FactorValueAssignment(
                    factor_id=factor_id, factor_value_id=factor_value_id
                )
                for factor_id, factor_value_id in filter.factor_values
            ),
        )
        patch_ = CombinationPatch(
            status=parse_status(patch.status) if patch.status is not None else None,
            output=patch.output,
            output_set=patch.output_set,
            impossible_reason=patch.impossible_reason,
            impossible_reason_set=patch.impossible_reason_set,
        )

        matched, updated = await self._combinations.bulk_update_status(
            table_id, filter_, patch_
        )
        return BulkPatchResult(matched_count=matched, updated_count=updated)
