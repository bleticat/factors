"""Use cases for the `combinations` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.combinations.entities import parse_status
from app.combinations.errors import CombinationNotFoundError
from app.combinations.ports.combination_queries import CombinationDTO
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    FactorValueAssignment,
)
from app.combinations.service import validate_factor_value_pairs
from app.shared.database.port import Database
from app.shared.errors import DuplicateFactorInAssignmentError
from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError


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


@dataclass(frozen=True)
class EvaluateResult:
    """`kind == "single"` for a full assignment (`combination` may still be
    `None` if nothing matches); `kind == "list"` for a partial/empty
    assignment (`page` holds every consistent combination)."""

    kind: str
    combination: CombinationDTO | None = None
    page: Page[CombinationDTO] | None = None


class CombinationsUseCases:
    """The `combinations` module's use cases. Constructed once with the
    app's `Database`."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

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
        async with self._database.unit_of_work() as uow:
            combination = await uow.combinations.get(table_id, combination_id)
            if combination is None:
                raise CombinationNotFoundError(combination_id)

            if status is not None:
                combination.status = parse_status(status)
            if output_set:
                combination.output = output
            if impossible_reason_set:
                combination.impossible_reason = impossible_reason

            await uow.combinations.save(combination)
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
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise DecisionTableNotFoundError(table_id)
            table.validate_factor_value_pairs(list(filter.factor_values))

            filter_ = CombinationFilter(
                status=parse_status(filter.status)
                if filter.status is not None
                else None,
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

            matched, updated = await uow.combinations.bulk_update_status(
                table_id, filter_, patch_
            )
            return BulkPatchResult(matched_count=matched, updated_count=updated)

    # --- Reads ------------------------------------------------------------------

    async def list_combinations(
        self,
        table_id: int,
        status: str | None = None,
        factor_values: tuple[tuple[int, int], ...] = (),
        page: PageRequest = PageRequest(),
    ) -> Page[CombinationDTO]:
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        validate_factor_value_pairs(table, list(factor_values))

        filter_ = CombinationFilter(
            status=parse_status(status) if status is not None else None,
            factor_values=tuple(
                FactorValueAssignment(
                    factor_id=factor_id, factor_value_id=factor_value_id
                )
                for factor_id, factor_value_id in factor_values
            ),
        )
        return await self._database.combinations_queries.list_(table_id, filter_, page)

    async def evaluate_combinations(
        self,
        table_id: int,
        assignment: tuple[tuple[int, int], ...] = (),
        page: PageRequest = PageRequest(),
    ) -> EvaluateResult:
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)

        factor_ids = [factor_id for factor_id, _ in assignment]
        seen: set[int] = set()
        for factor_id in factor_ids:
            if factor_id in seen:
                raise DuplicateFactorInAssignmentError(factor_id)
            seen.add(factor_id)

        validate_factor_value_pairs(table, list(assignment))

        is_full = bool(table.factors) and len(seen) == len(table.factors)

        if is_full:
            combination = (
                await self._database.combinations_queries.find_by_exact_assignment(
                    table_id, list(assignment)
                )
            )
            return EvaluateResult(kind="single", combination=combination)

        filter_ = CombinationFilter(
            factor_values=tuple(
                FactorValueAssignment(
                    factor_id=factor_id, factor_value_id=factor_value_id
                )
                for factor_id, factor_value_id in assignment
            )
        )
        result_page = await self._database.combinations_queries.list_(
            table_id, filter_, page
        )
        return EvaluateResult(kind="list", page=result_page)
