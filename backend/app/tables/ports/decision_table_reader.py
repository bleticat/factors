from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class FactorValueDTO:
    id: int
    value: str
    order_index: int


@dataclass(frozen=True)
class FactorDTO:
    id: int
    name: str
    order_index: int
    values: list[FactorValueDTO]


@dataclass(frozen=True)
class DecisionTableDTO:
    id: int
    name: str
    description: str | None
    factors: list[FactorDTO]


@dataclass(frozen=True)
class DecisionTableSummaryDTO:
    id: int
    name: str
    description: str | None
    factor_count: int


class DecisionTableReader(ABC):
    """Read-side port for the `DecisionTable` aggregate."""

    @abstractmethod
    async def get(self, table_id: int) -> DecisionTableDTO | None:
        """Return a decision table with its factors and values, or None if
        `table_id` doesn't exist."""

    @abstractmethod
    async def list_summaries(self, page: PageRequest) -> Page[DecisionTableSummaryDTO]:
        """Return a page of decision table summaries, most recently created first."""
