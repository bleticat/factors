from __future__ import annotations

from abc import ABC, abstractmethod

from app.decision_tables.domain.decision_table import DecisionTable


class DecisionTableRepository(ABC):
    """Write-side port for the `DecisionTable` aggregate (table + factors +
    values). Load whole, mutate in memory, save whole."""

    @abstractmethod
    async def add(self, table: DecisionTable) -> DecisionTable:
        """Insert a new table and populate its generated `id` in place."""

    @abstractmethod
    async def get(self, table_id: int) -> DecisionTable | None: ...

    @abstractmethod
    async def save(self, table: DecisionTable) -> None:
        """Reconcile the whole aggregate: update the table, insert/update/
        delete factors and values to match `table`'s current state, and
        populate generated ids on any newly-added factor/value in place."""

    @abstractmethod
    async def delete(self, table_id: int) -> None: ...
