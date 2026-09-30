"""Use cases for the `tables` module: the `DecisionTable` aggregate itself,
plus its child `Factor`/`FactorValue` entities (see `entities.py` for why
factors/values are part of this aggregate rather than modules of their
own). Write methods open their own transaction via `self._database.
unit_of_work()`; read methods call straight through to `self._database.
tables_queries` — no scope is ever injected from outside, and a method is
free to open more than one transaction if it genuinely has
independent-commit steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.errors import EmptyNameError, NotFoundError
from app.shared.pagination import Page, PageRequest
from app.shared.ports.database import Database
from app.tables.entities import DecisionTable
from app.tables.errors import (
    DuplicateFactorNameError,
    DuplicateFactorValueError,
)
from app.tables.ports.decision_table_queries import (
    DecisionTableDTO,
    DecisionTableSummaryDTO,
    FactorDTO,
)
from app.tables.service import ensure_not_generating

# --- Result shapes -----------------------------------------------------------
# Per ADR 002's guidance against "return full read-side projections from
# every command" (it couples write use cases to screen-specific read needs),
# writes return small confirmation/id-bearing DTOs of their own rather than
# reusing the nested query-side DTOs in `ports/decision_table_queries.py`.
# Callers that need the full picture follow up with a read (ADR 002's
# "command, then query" pattern).


@dataclass(frozen=True)
class DecisionTableRef:
    id: int
    name: str
    description: str | None


@dataclass(frozen=True)
class FactorRef:
    id: int
    name: str
    order_index: int


@dataclass(frozen=True)
class FactorValueRef:
    id: int
    value: str
    order_index: int


class TablesUseCases:
    """The `tables` module's use cases, one method each. Constructed once
    with the app's `Database` — cheap and stateless, since each method
    opens whatever it needs (a transaction for writes, nothing extra for
    reads) internally."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Decision table ------------------------------------------------------

    async def create_decision_table(
        self, name: str, description: str | None = None
    ) -> DecisionTableRef:
        """Create a new decision table.

        Raises:
            EmptyNameError: if `name` is blank.
        """
        if not name.strip():
            raise EmptyNameError("name")
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.add(
                DecisionTable(id=None, name=name, description=description)
            )
            assert table.id is not None
            return DecisionTableRef(
                id=table.id, name=table.name, description=table.description
            )

    async def update_decision_table(
        self,
        table_id: int,
        name: str | None = None,
        description: str | None = None,
        description_set: bool = False,
    ) -> DecisionTableRef:
        """Update a decision table's name and/or description.

        `description` is only applied when `description_set` is True, so a
        caller can distinguish "leave description alone" from "clear it".

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            EmptyNameError: if `name` is given but blank.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")

            if name is not None:
                if not name.strip():
                    raise EmptyNameError("name")
                table.name = name
            if description_set:
                table.description = description

            await uow.tables.save(table)
            return DecisionTableRef(
                id=table.id, name=table.name, description=table.description
            )

    async def delete_decision_table(self, table_id: int) -> None:
        """Delete a decision table. A no-op if `table_id` doesn't exist."""
        async with self._database.unit_of_work() as uow:
            await uow.tables.delete(table_id)

    # --- Factors --------------------------------------------------------------

    async def add_factor(self, table_id: int, name: str) -> FactorRef:
        """Add a new factor to a decision table.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            EmptyNameError: if `name` is blank.
            DuplicateFactorNameError: if `name` is already used in this table.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            factor = table.add_factor(name)
            await uow.tables.save(table)
            assert factor.id is not None
            return FactorRef(
                id=factor.id, name=factor.name, order_index=factor.order_index
            )

    async def update_factor(
        self,
        table_id: int,
        factor_id: int,
        name: str | None = None,
        order_index: int | None = None,
    ) -> FactorRef:
        """Update a factor's name and/or order index.

        Raises:
            NotFoundError: if `table_id` or `factor_id` doesn't exist.
            EmptyNameError: if `name` is given but blank.
            DuplicateFactorNameError: if `name` is already used by another
                factor in this table.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            if name is not None:
                if not name.strip():
                    raise EmptyNameError("name")
                if any(f.name == name and f.id != factor.id for f in table.factors):
                    raise DuplicateFactorNameError(name)
                factor.name = name
            if order_index is not None:
                factor.order_index = order_index

            await uow.tables.save(table)
            return FactorRef(
                id=factor.id, name=factor.name, order_index=factor.order_index
            )

    async def delete_factor(self, table_id: int, factor_id: int) -> None:
        """Delete a factor, cascading to every combination and rule for its
        table (both may reference the deleted factor).

        Raises:
            NotFoundError: if `table_id` or `factor_id` doesn't exist.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            table.factors = [f for f in table.factors if f.id != factor.id]
            await uow.tables.save(table)
            # Deleting a factor invalidates every existing combination's
            # signature (see spec 001) — cascade the whole set for this table.
            await uow.combinations.delete_all_for_table(table_id)
            # A rule's assignment may reference the deleted factor; rather
            # than silently narrowing its meaning, invalidate every rule for
            # this table too (see spec 005).
            await uow.rules.delete_all_for_table(table_id)

    # --- Factor values ----------------------------------------------------------

    async def add_factor_value(
        self, table_id: int, factor_id: int, value: str
    ) -> FactorValueRef:
        """Add a new value to a factor.

        Raises:
            NotFoundError: if `table_id` or `factor_id` doesn't exist.
            EmptyNameError: if `value` is blank.
            DuplicateFactorValueError: if `value` already exists on this factor.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            added = factor.add_value(value)
            await uow.tables.save(table)
            assert added.id is not None
            return FactorValueRef(
                id=added.id, value=added.value, order_index=added.order_index
            )

    async def update_factor_value(
        self,
        table_id: int,
        factor_id: int,
        value_id: int,
        value: str | None = None,
        order_index: int | None = None,
    ) -> FactorValueRef:
        """Update a factor value's value and/or order index.

        Raises:
            NotFoundError: if `table_id`, `factor_id`, or `value_id` doesn't exist.
            EmptyNameError: if `value` is given but blank.
            DuplicateFactorValueError: if `value` is already used by another
                value on this factor.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            existing = factor.get_value(value_id)
            if existing is None:
                raise NotFoundError(f"Factor value {value_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            if value is not None:
                if not value.strip():
                    raise EmptyNameError("value")
                if any(v.value == value and v.id != existing.id for v in factor.values):
                    raise DuplicateFactorValueError(value)
                existing.value = value
            if order_index is not None:
                existing.order_index = order_index

            await uow.tables.save(table)
            return FactorValueRef(
                id=existing.id, value=existing.value, order_index=existing.order_index
            )

    async def delete_factor_value(
        self, table_id: int, factor_id: int, value_id: int
    ) -> None:
        """Delete a factor value, cascading to every combination and rule
        for its table (both may reference the deleted value).

        Raises:
            NotFoundError: if `table_id`, `factor_id`, or `value_id` doesn't exist.
            GenerationInProgressError: if the table has a generation job running.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            value = factor.get_value(value_id)
            if value is None:
                raise NotFoundError(f"Factor value {value_id} not found")
            await ensure_not_generating(uow.jobs, table_id)

            factor.values = [v for v in factor.values if v.id != value.id]
            await uow.tables.save(table)
            # Same rationale as delete_factor: invalidates every existing
            # combination's signature for this table.
            await uow.combinations.delete_all_for_table(table_id)
            # Same rationale as delete_factor: a rule's assignment may
            # reference the deleted value (see spec 005).
            await uow.rules.delete_all_for_table(table_id)

    # --- Reads ------------------------------------------------------------------

    async def get_decision_table(self, table_id: int) -> DecisionTableDTO:
        """Return a decision table with its factors and their values.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise NotFoundError(f"Decision table {table_id} not found")
        return table

    async def list_decision_tables(
        self, page: PageRequest = PageRequest()
    ) -> Page[DecisionTableSummaryDTO]:
        """Return a page of decision table summaries, most recently created first."""
        return await self._database.tables_queries.list_summaries(page)

    async def list_factors(self, table_id: int) -> list[FactorDTO]:
        """Return a decision table's factors and their values.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise NotFoundError(f"Decision table {table_id} not found")
        return table.factors
