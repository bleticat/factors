from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.decision_tables.ports.combination_repository import CombinationFilter
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class CombinationValueDTO:
    factor_id: int
    factor_value_id: int


@dataclass(frozen=True)
class CombinationDTO:
    id: int
    decision_table_id: int
    status: str
    output: str | None
    impossible_reason: str | None
    values: list[CombinationValueDTO]


class CombinationQueries(ABC):
    @abstractmethod
    async def list_(
        self, table_id: int, filter_: CombinationFilter, page: PageRequest
    ) -> Page[CombinationDTO]: ...

    @abstractmethod
    async def get(self, table_id: int, combination_id: int) -> CombinationDTO | None: ...

    @abstractmethod
    async def find_by_exact_assignment(
        self, table_id: int, assignment: list[tuple[int, int]]
    ) -> CombinationDTO | None:
        """Full-assignment evaluate: the assignment covers every factor of
        the table, so at most one combination can match."""
