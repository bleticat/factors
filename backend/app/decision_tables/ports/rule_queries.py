from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True)
class RuleValueDTO:
    factor_id: int
    factor_value_id: int


@dataclass(frozen=True)
class RuleDTO:
    id: int
    decision_table_id: int
    output: str
    factor_values: list[RuleValueDTO] = field(default_factory=list)
    matched_count: int = 0
    applied_at: datetime | None = None
    created_at: datetime | None = None


class RuleQueries(ABC):
    @abstractmethod
    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[RuleDTO]: ...

    @abstractmethod
    async def get(self, table_id: int, rule_id: int) -> RuleDTO | None: ...
