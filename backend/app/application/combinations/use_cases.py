"""Use cases for the `combinations` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.combinations.ports.queries import CombinationDTO
from app.application.combinations.ports.repository import (
    CombinationFilter,
    CombinationPatch,
    FactorValueAssignment,
)
from app.application.pagination import Page, PageRequest
from app.application.ports.database import Database
from app.application.tables.ports.queries import DecisionTableDTO
from app.domain.combinations.entities import parse_status
from app.domain.errors import DuplicateFactorInAssignmentError, NotFoundError
from app.domain.tables.errors import (
    UnknownFactorInFilterError,
    UnknownFactorValueInFilterError,
)


def validate_factor_value_pairs(
    table: DecisionTableDTO, pairs: list[tuple[int, int]]
) -> None:
    """Validates against the `DecisionTableDTO` read shape rather than the
    `DecisionTable` domain aggregate (that variant, `DecisionTable.
    validate_factor_value_pairs`, is used by write methods, which do have
    write-side repository access)."""
    factors_by_id = {f.id: f for f in table.factors}
    for factor_id, factor_value_id in pairs:
        factor = factors_by_id.get(factor_id)
        if factor is None:
            raise UnknownFactorInFilterError(factor_id, table.id)
        if not any(v.id == factor_value_id for v in factor.values):
            raise UnknownFactorValueInFilterError(factor_value_id, factor_id)


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
                raise NotFoundError(f"Combination {combination_id} not found")

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
                raise NotFoundError(f"Decision table {table_id} not found")
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
            raise NotFoundError(f"Decision table {table_id} not found")
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
            raise NotFoundError(f"Decision table {table_id} not found")

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
