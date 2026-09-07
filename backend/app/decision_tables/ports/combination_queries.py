from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.decision_tables.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
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


@dataclass(frozen=True)
class RuleFilterInput:
    """One rule's identity + assignment, as needed to compile it into the
    same filter shape `apply_combination_filter` already understands — used
    by `list_matched_by_multiple_rules` (spec 006) instead of depending on
    `ports/rule_queries.RuleDTO` directly, so this port doesn't couple to
    another port's read model."""

    rule_id: int
    output: str
    factor_values: tuple[FactorValueAssignment, ...]


@dataclass(frozen=True)
class RuleTagDTO:
    id: int
    output: str


@dataclass(frozen=True)
class CombinationOverlapDTO:
    combination: CombinationDTO
    matching_rules: list[RuleTagDTO]  # ordered by rule id ascending; last is the current winner (spec 005)


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

    @abstractmethod
    async def list_matched_by_multiple_rules(
        self, table_id: int, rules: list[RuleFilterInput], page: PageRequest
    ) -> Page[CombinationOverlapDTO]:
        """Rows matched by 2+ of the given rules' assignments (spec 006).
        Callers pass every rule for the table; a caller passing fewer than
        two rules gets an empty page back."""
