from abc import ABC, abstractmethod
from dataclasses import dataclass

from factors.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class DecisionTableSummary:
    id: int
    name: str
    description: str | None
    factor_count: int


class DecisionTableReader(ABC):
    @abstractmethod
    async def list_summaries(self, page: PageRequest) -> Page[DecisionTableSummary]: ...
