"""Read-side use cases for the `combinations` module."""

from __future__ import annotations

from dataclasses import dataclass, field

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
from app.shared.mediator.requests import Query
from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_queries import DecisionTableQueries


@dataclass(frozen=True)
class ListCombinationsQuery(Query[Page[CombinationDTO]]):
    table_id: int
    status: str | None = None
    factor_values: tuple[tuple[int, int], ...] = ()
    page: PageRequest = field(default_factory=PageRequest)


class ListCombinationsHandler:
    def __init__(self, tables: DecisionTableQueries, combinations: CombinationQueries) -> None:
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: ListCombinationsQuery) -> Page[CombinationDTO]:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        validate_factor_value_pairs(table, list(request.factor_values))

        filter_ = CombinationFilter(
            status=parse_status(request.status) if request.status is not None else None,
            factor_values=tuple(
                FactorValueAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ),
        )
        return await self._combinations.list_(request.table_id, filter_, request.page)


@dataclass(frozen=True)
class EvaluateResult:
    """`kind == "single"` for a full assignment (`combination` may still be
    `None` if nothing matches); `kind == "list"` for a partial/empty
    assignment (`page` holds every consistent combination)."""

    kind: str
    combination: CombinationDTO | None = None
    page: Page[CombinationDTO] | None = None


@dataclass(frozen=True)
class EvaluateCombinationsQuery(Query[EvaluateResult]):
    table_id: int
    assignment: tuple[tuple[int, int], ...] = ()
    page: PageRequest = field(default_factory=PageRequest)


class EvaluateCombinationsHandler:
    def __init__(self, tables: DecisionTableQueries, combinations: CombinationQueries) -> None:
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: EvaluateCombinationsQuery) -> EvaluateResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        factor_ids = [factor_id for factor_id, _ in request.assignment]
        seen: set[int] = set()
        for factor_id in factor_ids:
            if factor_id in seen:
                raise DuplicateFactorInAssignmentError(factor_id)
            seen.add(factor_id)

        validate_factor_value_pairs(table, list(request.assignment))

        is_full = bool(table.factors) and len(seen) == len(table.factors)

        if is_full:
            combination = await self._combinations.find_by_exact_assignment(
                request.table_id, list(request.assignment)
            )
            return EvaluateResult(kind="single", combination=combination)

        filter_ = CombinationFilter(
            factor_values=tuple(
                FactorValueAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.assignment
            )
        )
        page = await self._combinations.list_(request.table_id, filter_, request.page)
        return EvaluateResult(kind="list", page=page)
