"""Read-side use cases for the `tables` module."""

from __future__ import annotations

from app.shared.pagination import Page, PageRequest
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_queries import (
    DecisionTableDTO,
    DecisionTableQueries,
    DecisionTableSummaryDTO,
    FactorDTO,
)


class TablesQueries:
    """The `tables` module's read-side use cases. Built per call by
    `app.composition.build_tables_queries`."""

    def __init__(self, tables: DecisionTableQueries) -> None:
        self._tables = tables

    async def get_decision_table(self, table_id: int) -> DecisionTableDTO:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        return table

    async def list_decision_tables(
        self, page: PageRequest = PageRequest()
    ) -> Page[DecisionTableSummaryDTO]:
        return await self._tables.list_summaries(page)

    async def list_factors(self, table_id: int) -> list[FactorDTO]:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        return table.factors
