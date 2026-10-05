from abc import ABC, abstractmethod

from factors.features.rules.entities import Rule
from factors.shared.pagination import Page, PageRequest


class RuleReader(ABC):
    @abstractmethod
    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[Rule]: ...

    @abstractmethod
    async def list_all_for_table(self, table_id: int) -> list[Rule]: ...
