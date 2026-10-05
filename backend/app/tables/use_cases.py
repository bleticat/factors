"""Use cases for the `tables` module: the `DecisionTable` aggregate itself,
plus its child `Factor`/`FactorValue` entities (see `entities.py` for why
factors/values are part of this aggregate rather than modules of their
own). Every method opens its own scope via `self._database`: a write opens
`transaction()` (commits on clean exit, rolls back on exception), a read
opens `snapshot()` (always rolls back). A method is free to open more than
one if it genuinely has independent-commit steps, or a write method can
read through the same `transaction()` it writes through — see
`add_factor`'s `db.tables.get(...)` below.
"""

from dataclasses import dataclass

from app.shared.errors import InvariantViolationError, NotFoundError, ValidationError
from app.shared.pagination import Page, PageRequest
from app.shared.ports.database import Database
from app.tables.entities import DecisionTable
from app.tables.ports.decision_table_reader import (
    DecisionTableDTO,
    DecisionTableSummaryDTO,
    FactorDTO,
)
from app.tables.service import ensure_not_generating

# --- Result shapes -----------------------------------------------------------
# Per ADR 002's guidance against "return full read-side projections from
# every command" (it couples write use cases to screen-specific read needs),
# writes return small confirmation/id-bearing DTOs of their own rather than
# reusing the nested query-side DTOs in `ports/decision_table_reader.py`.
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
    opens whatever it needs (a transaction for writes, a snapshot for
    reads) internally."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Decision table ------------------------------------------------------

    async def create_decision_table(
        self, name: str, description: str | None = None
    ) -> DecisionTableRef:
        """Create a new decision table.

        Raises:
            ValidationError: if `name` is blank.
        """
        if not name.strip():
            raise ValidationError("name must not be empty")
        async with self._database.transaction() as db:
            table = await db.tables.add(
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
            ValidationError: if `name` is given but blank.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")

            if name is not None:
                if not name.strip():
                    raise ValidationError("name must not be empty")
                table.name = name
            if description_set:
                table.description = description

            await db.tables.save(table)
            return DecisionTableRef(
                id=table.id, name=table.name, description=table.description
            )

    async def delete_decision_table(self, table_id: int) -> None:
        """Delete a decision table. A no-op if `table_id` doesn't exist."""
        async with self._database.transaction() as db:
            await db.tables.delete(table_id)

    # --- Factors --------------------------------------------------------------

    async def add_factor(self, table_id: int, name: str) -> FactorRef:
        """Add a new factor to a decision table.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            ValidationError: if `name` is blank.
            InvariantViolationError: if `name` is already used in this
                table, or the table has a generation job running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            factor = table.add_factor(name)
            await db.tables.save(table)
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
            ValidationError: if `name` is given but blank.
            InvariantViolationError: if `name` is already used by another
                factor in this table, or the table has a generation job
                running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            if name is not None:
                if not name.strip():
                    raise ValidationError("name must not be empty")
                if any(f.name == name and f.id != factor.id for f in table.factors):
                    raise InvariantViolationError(
                        f"Factor name {name!r} is already used in this table"
                    )
                factor.name = name
            if order_index is not None:
                factor.order_index = order_index

            await db.tables.save(table)
            return FactorRef(
                id=factor.id, name=factor.name, order_index=factor.order_index
            )

    async def delete_factor(self, table_id: int, factor_id: int) -> None:
        """Delete a factor, cascading to every combination and rule for its
        table (both may reference the deleted factor).

        Raises:
            NotFoundError: if `table_id` or `factor_id` doesn't exist.
            InvariantViolationError: if the table has a generation job running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            table.factors = [f for f in table.factors if f.id != factor.id]
            await db.tables.save(table)
            # Deleting a factor invalidates every existing combination's
            # signature (see spec 001) — cascade the whole set for this table.
            await db.combinations.delete_all_for_table(table_id)
            # A rule's assignment may reference the deleted factor; rather
            # than silently narrowing its meaning, invalidate every rule for
            # this table too (see spec 005).
            await db.rules.delete_all_for_table(table_id)

    # --- Factor values ----------------------------------------------------------

    async def add_factor_value(
        self, table_id: int, factor_id: int, value: str
    ) -> FactorValueRef:
        """Add a new value to a factor.

        Raises:
            NotFoundError: if `table_id` or `factor_id` doesn't exist.
            ValidationError: if `value` is blank.
            InvariantViolationError: if `value` already exists on this
                factor, or the table has a generation job running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            added = factor.add_value(value)
            await db.tables.save(table)
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
            ValidationError: if `value` is given but blank.
            InvariantViolationError: if `value` is already used by another
                value on this factor, or the table has a generation job
                running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            existing = factor.get_value(value_id)
            if existing is None:
                raise NotFoundError(f"Factor value {value_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            if value is not None:
                if not value.strip():
                    raise ValidationError("value must not be empty")
                if any(v.value == value and v.id != existing.id for v in factor.values):
                    raise InvariantViolationError(
                        f"Value {value!r} is already used in this factor"
                    )
                existing.value = value
            if order_index is not None:
                existing.order_index = order_index

            await db.tables.save(table)
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
            InvariantViolationError: if the table has a generation job running.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            factor = table.get_factor(factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {factor_id} not found")
            value = factor.get_value(value_id)
            if value is None:
                raise NotFoundError(f"Factor value {value_id} not found")
            await ensure_not_generating(db.jobs, table_id)

            factor.values = [v for v in factor.values if v.id != value.id]
            await db.tables.save(table)
            # Same rationale as delete_factor: invalidates every existing
            # combination's signature for this table.
            await db.combinations.delete_all_for_table(table_id)
            # Same rationale as delete_factor: a rule's assignment may
            # reference the deleted value (see spec 005).
            await db.rules.delete_all_for_table(table_id)

    # --- Reads ------------------------------------------------------------------

    async def get_decision_table(self, table_id: int) -> DecisionTableDTO:
        """Return a decision table with its factors and their values.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        async with self._database.snapshot() as db:
            table = await db.tables_reader.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            return table

    async def list_decision_tables(
        self, page: PageRequest = PageRequest()
    ) -> Page[DecisionTableSummaryDTO]:
        """Return a page of decision table summaries, most recently created first."""
        async with self._database.snapshot() as db:
            return await db.tables_reader.list_summaries(page)

    async def list_factors(self, table_id: int) -> list[FactorDTO]:
        """Return a decision table's factors and their values.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        async with self._database.snapshot() as db:
            table = await db.tables_reader.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            return table.factors
