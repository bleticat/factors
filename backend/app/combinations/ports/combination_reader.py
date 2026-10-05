from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.combinations.entities import Combination
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class RuleFilterInput:
    rule_id: int
    output: str
    title: str | None
    factor_values: tuple[FactorValueAssignment, ...]


@dataclass(frozen=True)
class RuleTag:
    id: int
    output: str
    title: str | None


@dataclass(frozen=True)
class CombinationOverlap:
    combination: Combination
    matching_rules: list[
        RuleTag
    ]  # ordered by rule id ascending; last is the current winner (spec 005)


class CombinationReader(ABC):
    @abstractmethod
    async def list_(
        self, table_id: int, filter_: CombinationFilter, page: PageRequest
    ) -> Page[Combination]: ...

    @abstractmethod
    async def find_by_exact_assignment(
        self, table_id: int, assignment: list[tuple[int, int]]
    ) -> Combination | None: ...

    @abstractmethod
    async def list_matched_by_multiple_rules(
        self, table_id: int, rules: list[RuleFilterInput], page: PageRequest
    ) -> Page[CombinationOverlap]: ...

    @abstractmethod
    async def count_shadowed_matches(
        self, table_id: int, ordered_rules: list[RuleFilterInput]
    ) -> dict[int, int]: ...
