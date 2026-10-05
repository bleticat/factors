"""Use cases for the `combinations` module."""

from dataclasses import dataclass

from app.combinations.entities import parse_status
from app.combinations.ports.combination_reader import CombinationDTO
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    FactorValueAssignment,
)
from app.shared.errors import NotFoundError, ValidationError
from app.shared.pagination import Page, PageRequest
from app.shared.ports.database import Database


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
        """Update a single combination's status, output, and/or impossible reason.

        `output`/`impossible_reason` are only applied when their `_set` flag
        is True, so a caller can distinguish "leave alone" from "clear it".

        Raises:
            NotFoundError: if `table_id`/`combination_id` doesn't exist.
            ValidationError: if `status` isn't a valid status.
        """
        async with self._database.transaction() as db:
            combination = await db.combinations.get(table_id, combination_id)
            if combination is None:
                raise NotFoundError(f"Combination {combination_id} not found")

            if status is not None:
                combination.status = parse_status(status)
            if output_set:
                combination.output = output
            if impossible_reason_set:
                combination.impossible_reason = impossible_reason

            await db.combinations.save(combination)
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
        """Apply `patch` to every combination in `table_id` matching `filter`.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            ValidationError: if a filter pair names a factor or value not on
                this table, or a status string in `filter`/`patch` isn't a
                valid status.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
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

            matched, updated = await db.combinations.bulk_update_status(
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
        """List a decision table's combinations, optionally filtered by
        status and/or factor-value assignment.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            ValidationError: if a filter pair names a factor or value not on
                this table, or `status` isn't a valid status.
        """
        async with self._database.snapshot() as db:
            # `db.tables` (the write-side repository) is used here even
            # though this is a read-only method: it's the one that returns
            # the full `DecisionTable` entity, whose own
            # `validate_factor_value_pairs` this validation reuses rather
            # than duplicating against a separate read-side DTO shape.
            # Reading through it does no harm — nothing in this method ever
            # calls `save`/`add`/`delete`, so there's nothing for the
            # snapshot's guaranteed rollback to undo.
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            table.validate_factor_value_pairs(list(factor_values))

            filter_ = CombinationFilter(
                status=parse_status(status) if status is not None else None,
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=factor_id, factor_value_id=factor_value_id
                    )
                    for factor_id, factor_value_id in factor_values
                ),
            )
            return await db.combinations_reader.list_(table_id, filter_, page)

    async def evaluate_combinations(
        self,
        table_id: int,
        assignment: tuple[tuple[int, int], ...] = (),
        page: PageRequest = PageRequest(),
    ) -> EvaluateResult:
        """Evaluate a (possibly partial) factor-value assignment against a
        decision table's combinations.

        A full assignment (one value per factor) returns the single matching
        combination, if any (`kind == "single"`); a partial or empty
        assignment returns every consistent combination as a page
        (`kind == "list"`).

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            ValidationError: if `assignment` names the same factor twice, or
                names a factor or value not on this table.
        """
        async with self._database.snapshot() as db:
            table = await db.tables.get(table_id)  # see list_combinations above
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")

            factor_ids = [factor_id for factor_id, _ in assignment]
            seen: set[int] = set()
            for factor_id in factor_ids:
                if factor_id in seen:
                    raise ValidationError(
                        f"Factor {factor_id} is assigned more than once in "
                        "the same request"
                    )
                seen.add(factor_id)

            table.validate_factor_value_pairs(list(assignment))

            is_full = bool(table.factors) and len(seen) == len(table.factors)

            if is_full:
                combination = await db.combinations_reader.find_by_exact_assignment(
                    table_id, list(assignment)
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
            result_page = await db.combinations_reader.list_(table_id, filter_, page)
            return EvaluateResult(kind="list", page=result_page)
