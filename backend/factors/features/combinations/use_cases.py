from dataclasses import dataclass, field

from factors.features.combinations.entities import Combination, parse_status
from factors.features.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    FactorValueAssignment,
)
from factors.shared.errors import NotFoundError, ValidationError
from factors.shared.pagination import Page, PageRequest
from factors.shared.ports.database import Database

# --- Requests/responses -------------------------------------------------


@dataclass(frozen=True)
class PatchCombinationRequest:
    table_id: int
    combination_id: int
    status: str | None = None
    output: str | None = None
    output_set: bool = False
    impossible_reason: str | None = None
    impossible_reason_set: bool = False


@dataclass(frozen=True)
class PatchCombinationResponse:
    combination: Combination


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
class BulkPatchCombinationsRequest:
    table_id: int
    filter: BulkFilterInput = field(default_factory=BulkFilterInput)
    patch: BulkPatchInput = field(default_factory=BulkPatchInput)


@dataclass(frozen=True)
class BulkPatchCombinationsResponse:
    matched_count: int
    updated_count: int


@dataclass(frozen=True)
class ListCombinationsRequest:
    table_id: int
    status: str | None = None
    factor_values: tuple[tuple[int, int], ...] = ()
    page: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True)
class ListCombinationsResponse:
    page: Page[Combination]


@dataclass(frozen=True)
class EvaluateCombinationsRequest:
    table_id: int
    assignment: tuple[tuple[int, int], ...] = ()
    page: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True)
class EvaluateCombinationsResponse:
    kind: str
    combination: Combination | None = None
    page: Page[Combination] | None = None


class CombinationsUseCases:
    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def patch_combination(
        self, request: PatchCombinationRequest
    ) -> PatchCombinationResponse:
        async with self._database.transaction() as db:
            combination = await db.combinations.get(
                request.table_id, request.combination_id
            )
            if combination is None:
                raise NotFoundError(f"Combination {request.combination_id} not found")

            if request.status is not None:
                combination.status = parse_status(request.status)
            if request.output_set:
                combination.output = request.output
            if request.impossible_reason_set:
                combination.impossible_reason = request.impossible_reason

            await db.combinations.save(combination)
            return PatchCombinationResponse(combination=combination)

    async def bulk_patch_combinations(
        self, request: BulkPatchCombinationsRequest
    ) -> BulkPatchCombinationsResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            table.validate_factor_value_pairs(list(request.filter.factor_values))

            filter_ = CombinationFilter(
                status=parse_status(request.filter.status)
                if request.filter.status is not None
                else None,
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=factor_id, factor_value_id=factor_value_id
                    )
                    for factor_id, factor_value_id in request.filter.factor_values
                ),
            )
            patch_ = CombinationPatch(
                status=parse_status(request.patch.status)
                if request.patch.status is not None
                else None,
                output=request.patch.output,
                output_set=request.patch.output_set,
                impossible_reason=request.patch.impossible_reason,
                impossible_reason_set=request.patch.impossible_reason_set,
            )

            matched, updated = await db.combinations.bulk_update_status(
                request.table_id, filter_, patch_
            )
            return BulkPatchCombinationsResponse(
                matched_count=matched, updated_count=updated
            )

    # --- Reads ------------------------------------------------------------------

    async def list_combinations(
        self, request: ListCombinationsRequest
    ) -> ListCombinationsResponse:
        async with self._database.snapshot() as db:
            # `db.tables` (the write-side repository) is used here even
            # though this is a read-only method: it's the one that returns
            # the full `DecisionTable` entity, whose own
            # `validate_factor_value_pairs` this validation reuses rather
            # than duplicating against a separate read-side shape.
            # Reading through it does no harm — nothing in this method ever
            # calls `save`/`add`/`delete`, so there's nothing for the
            # snapshot's guaranteed rollback to undo.
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            table.validate_factor_value_pairs(list(request.factor_values))

            filter_ = CombinationFilter(
                status=parse_status(request.status)
                if request.status is not None
                else None,
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=factor_id, factor_value_id=factor_value_id
                    )
                    for factor_id, factor_value_id in request.factor_values
                ),
            )
            page = await db.combinations_reader.list_(
                request.table_id, filter_, request.page
            )
            return ListCombinationsResponse(page=page)

    async def evaluate_combinations(
        self, request: EvaluateCombinationsRequest
    ) -> EvaluateCombinationsResponse:
        async with self._database.snapshot() as db:
            table = await db.tables.get(request.table_id)  # see list_combinations above
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            factor_ids = [factor_id for factor_id, _ in request.assignment]
            seen: set[int] = set()
            for factor_id in factor_ids:
                if factor_id in seen:
                    raise ValidationError(
                        f"Factor {factor_id} is assigned more than once in "
                        "the same request"
                    )
                seen.add(factor_id)

            table.validate_factor_value_pairs(list(request.assignment))

            is_full = bool(table.factors) and len(seen) == len(table.factors)

            if is_full:
                combination = await db.combinations_reader.find_by_exact_assignment(
                    request.table_id, list(request.assignment)
                )
                return EvaluateCombinationsResponse(
                    kind="single", combination=combination
                )

            filter_ = CombinationFilter(
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=factor_id, factor_value_id=factor_value_id
                    )
                    for factor_id, factor_value_id in request.assignment
                )
            )
            result_page = await db.combinations_reader.list_(
                request.table_id, filter_, request.page
            )
            return EvaluateCombinationsResponse(kind="list", page=result_page)
