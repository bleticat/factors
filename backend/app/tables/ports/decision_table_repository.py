from abc import ABC, abstractmethod

from app.tables.entities import DecisionTable


class DecisionTableRepository(ABC):
    @abstractmethod
    async def add(self, table: DecisionTable) -> DecisionTable: ...

    @abstractmethod
    async def get(self, table_id: int) -> DecisionTable | None: ...

    @abstractmethod
    async def save(self, table: DecisionTable) -> None: ...

    @abstractmethod
    async def delete(self, table_id: int) -> None: ...
