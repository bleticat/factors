from __future__ import annotations

from dataclasses import dataclass, field

from app.decision_tables.commands.results import BulkPatchResult
from app.decision_tables.domain.combination import parse_status
from app.decision_tables.domain.errors import DecisionTableNotFoundError
from app.decision_tables.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    CombinationRepository,
    FactorValueAssignment,
)
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.shared.mediator.requests import Command


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


@dataclass(frozen=True)
class BulkPatchCombinationsCommand(Command[BulkPatchResult]):
    table_id: int
    filter: BulkFilterInput = field(default_factory=BulkFilterInput)
    patch: BulkPatchInput = field(default_factory=BulkPatchInput)


class BulkPatchCombinationsHandler:
    def __init__(self, tables: DecisionTableRepository, combinations: CombinationRepository) -> None:
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: BulkPatchCombinationsCommand) -> BulkPatchResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        table.validate_factor_value_pairs(list(request.filter.factor_values))

        filter_ = CombinationFilter(
            status=parse_status(request.filter.status) if request.filter.status is not None else None,
            factor_values=tuple(
                FactorValueAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.filter.factor_values
            ),
        )
        patch = CombinationPatch(
            status=parse_status(request.patch.status) if request.patch.status is not None else None,
            output=request.patch.output,
            output_set=request.patch.output_set,
            impossible_reason=request.patch.impossible_reason,
            impossible_reason_set=request.patch.impossible_reason_set,
        )

        matched, updated = await self._combinations.bulk_update_status(request.table_id, filter_, patch)
        return BulkPatchResult(matched_count=matched, updated_count=updated)
