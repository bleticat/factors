"""Read-side port for `DecisionTable` list views.

A single table's full aggregate is loaded the same way for both reads and
writes — `DecisionTableRepository.get` — since there's no read-only
projection of the full aggregate distinct from the entity itself. The one
thing this port adds is `list_summaries`: a genuinely different shape
(`factor_count` instead of each factor's full value list) that exists
specifically so a list view doesn't have to eager-load every table's
factors and values just to show how many there are.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class DecisionTableSummary:
    """A list-view projection, not the `DecisionTable` aggregate: swaps the
    full `factors` list for a count, so `list_summaries` doesn't have to
    load every table's factors and values just to paginate a list."""

    id: int
    name: str
    description: str | None
    factor_count: int


class DecisionTableReader(ABC):
    """Read-side port for `DecisionTable` list views."""

    @abstractmethod
    async def list_summaries(self, page: PageRequest) -> Page[DecisionTableSummary]:
        """Return a page of decision table summaries, most recently created first."""
