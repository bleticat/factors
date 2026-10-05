from abc import ABC, abstractmethod
from datetime import datetime

from app.rules.entities import Rule


class RuleRepository(ABC):
    @abstractmethod
    async def add(self, rule: Rule) -> Rule: ...

    @abstractmethod
    async def get(self, table_id: int, rule_id: int) -> Rule | None: ...

    @abstractmethod
    async def list_for_table(self, table_id: int) -> list[Rule]: ...

    @abstractmethod
    async def save(self, rule: Rule) -> None: ...

    @abstractmethod
    async def delete(self, table_id: int, rule_id: int) -> bool: ...

    @abstractmethod
    async def delete_all_for_table(self, table_id: int) -> None: ...

    @abstractmethod
    async def record_apply(
        self, rule_id: int, matched_count: int, applied_at: datetime
    ) -> None: ...
