"""Read-side use cases for the `combinations` module."""

from __future__ import annotations

from dataclasses import dataclass

from app.combinations.entities import parse_status
from app.combinations.ports.combination_queries import (
    CombinationDTO,
    CombinationQueries,
)
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
from app.combinations.service import validate_factor_value_pairs
from app.shared.errors import DuplicateFactorInAssignmentError
from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_queries import DecisionTableQueries


@dataclass(frozen=True)
class EvaluateResult:
    """`kind == "single"` for a full assignment (`combination` may still be
    `None` if nothing matches); `kind == "list"` for a partial/empty
    assignment (`page` holds every consistent combination)."""

    kind: str
    combination: CombinationDTO | None = None
    page: Page[CombinationDTO] | None = None


class CombinationsQueries:
    """The `combinations` module's read-side use cases. Built per call by
    `app.composition.build_combinations_queries`."""

    def __init__(
        self, tables: DecisionTableQueries, combinations: CombinationQueries
    ) -> None:
        self._tables = tables
        self._combinations = combinations

    async def list_combinations(
        self,
        table_id: int,
        status: str | None = None,
        factor_values: tuple[tuple[int, int], ...] = (),
        page: PageRequest = PageRequest(),
    ) -> Page[CombinationDTO]:
        table = await self._tables.get(table_id)
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
        return await self._combinations.list_(table_id, filter_, page)

    async def evaluate_combinations(
        self,
        table_id: int,
        assignment: tuple[tuple[int, int], ...] = (),
        page: PageRequest = PageRequest(),
    ) -> EvaluateResult:
        table = await self._tables.get(table_id)
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
            combination = await self._combinations.find_by_exact_assignment(
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
        result_page = await self._combinations.list_(table_id, filter_, page)
        return EvaluateResult(kind="list", page=result_page)
