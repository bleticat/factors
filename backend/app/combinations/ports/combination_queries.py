from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.combinations.ports.combination_repository import (
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
    `app.rules.ports.rule_queries.RuleDTO` directly, so this port doesn't
    couple to another module's read model."""

    rule_id: int
    output: str
    title: str | None
    factor_values: tuple[FactorValueAssignment, ...]


@dataclass(frozen=True)
class RuleTagDTO:
    id: int
    output: str
    title: str | None


@dataclass(frozen=True)
class CombinationOverlapDTO:
    combination: CombinationDTO
    matching_rules: list[
        RuleTagDTO
    ]  # ordered by rule id ascending; last is the current winner (spec 005)


class CombinationQueries(ABC):
    """Read-side port for `Combination`/`CombinationValue`."""

    @abstractmethod
    async def list_(
        self, table_id: int, filter_: CombinationFilter, page: PageRequest
    ) -> Page[CombinationDTO]:
        """Return a page of a decision table's combinations matching `filter_`."""

    @abstractmethod
    async def get(self, table_id: int, combination_id: int) -> CombinationDTO | None:
        """Return one combination, or None if it doesn't exist on this table."""

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

    @abstractmethod
    async def count_shadowed_matches(
        self, table_id: int, ordered_rules: list[RuleFilterInput]
    ) -> dict[int, int]:
        """Spec 009: rules are no longer prevented from being more general
        than one another, so a rule can end up **shadowed** — some or all of
        the rows it matches are also matched by a rule later in `ordered_rules`
        (list order = apply order), whose output wins instead after a
        reapply. Returns `{rule_id: shadowed_count}` — how many of that
        rule's own matched rows currently show a *different* rule's output,
        for every rule that has at least one such row (a rule with none is
        simply absent from the result, not present with 0)."""
