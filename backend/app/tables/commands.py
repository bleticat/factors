"""Write-side use cases for the `tables` module: the `DecisionTable`
aggregate itself, plus its child `Factor`/`FactorValue` entities (see
`entities.py` for why factors/values are part of this aggregate rather than
modules of their own).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.combinations.ports.combination_repository import CombinationRepository
from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.rules.ports.rule_repository import RuleRepository
from app.shared.errors import EmptyNameError
from app.tables.entities import DecisionTable
from app.tables.errors import (
    DecisionTableNotFoundError,
    DuplicateFactorNameError,
    DuplicateFactorValueError,
    FactorNotFoundError,
    FactorValueNotFoundError,
)
from app.tables.ports.decision_table_repository import DecisionTableRepository
from app.tables.service import ensure_not_generating

# --- Command result shapes -------------------------------------------------
# Per ADR 002's guidance against "return full read-side projections from
# every command" (it couples write use cases to screen-specific read needs),
# commands return small confirmation/id-bearing DTOs of their own rather than
# reusing the nested query-side DTOs in `ports/decision_table_queries.py`.
# Callers that need the full picture follow up with a query (ADR 002's
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


class TablesCommands:
    """The `tables` module's write-side use cases, one method each. Built
    per call (one instance per unit of work) by `app.composition.
    build_tables_commands`; see `app/shared/api.py` / `app/shared/
    execution.py` for how boundaries obtain a unit of work to build it
    with."""

    def __init__(
        self,
        tables: DecisionTableRepository,
        jobs: GenerationJobRepository,
        combinations: CombinationRepository,
        rules: RuleRepository,
    ) -> None:
        self._tables = tables
        self._jobs = jobs
        self._combinations = combinations
        self._rules = rules

    # --- Decision table ----------------------------------------------------

    async def create_decision_table(
        self, name: str, description: str | None = None
    ) -> DecisionTableRef:
        if not name.strip():
            raise EmptyNameError("name")
        table = await self._tables.add(
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
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)

        if name is not None:
            if not name.strip():
                raise EmptyNameError("name")
            table.name = name
        if description_set:
            table.description = description

        await self._tables.save(table)
        return DecisionTableRef(
            id=table.id, name=table.name, description=table.description
        )

    async def delete_decision_table(self, table_id: int) -> None:
        await self._tables.delete(table_id)

    # --- Factors -------------------------------------------------------------

    async def add_factor(self, table_id: int, name: str) -> FactorRef:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        await ensure_not_generating(self._jobs, table_id)

        factor = table.add_factor(name)
        await self._tables.save(table)
        assert factor.id is not None
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)

    async def update_factor(
        self,
        table_id: int,
        factor_id: int,
        name: str | None = None,
        order_index: int | None = None,
    ) -> FactorRef:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        factor = table.get_factor(factor_id)
        if factor is None:
            raise FactorNotFoundError(factor_id)
        await ensure_not_generating(self._jobs, table_id)

        if name is not None:
            if not name.strip():
                raise EmptyNameError("name")
            if any(f.name == name and f.id != factor.id for f in table.factors):
                raise DuplicateFactorNameError(name)
            factor.name = name
        if order_index is not None:
            factor.order_index = order_index

        await self._tables.save(table)
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)

    async def delete_factor(self, table_id: int, factor_id: int) -> None:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        factor = table.get_factor(factor_id)
        if factor is None:
            raise FactorNotFoundError(factor_id)
        await ensure_not_generating(self._jobs, table_id)

        table.factors = [f for f in table.factors if f.id != factor.id]
        await self._tables.save(table)
        # Deleting a factor invalidates every existing combination's
        # signature (see spec 001) — cascade the whole set for this table.
        await self._combinations.delete_all_for_table(table_id)
        # A rule's assignment may reference the deleted factor; rather than
        # silently narrowing its meaning, invalidate every rule for this
        # table too (see spec 005).
        await self._rules.delete_all_for_table(table_id)

    # --- Factor values ---------------------------------------------------------

    async def add_factor_value(
        self, table_id: int, factor_id: int, value: str
    ) -> FactorValueRef:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        factor = table.get_factor(factor_id)
        if factor is None:
            raise FactorNotFoundError(factor_id)
        await ensure_not_generating(self._jobs, table_id)

        added = factor.add_value(value)
        await self._tables.save(table)
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
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        factor = table.get_factor(factor_id)
        if factor is None:
            raise FactorNotFoundError(factor_id)
        existing = factor.get_value(value_id)
        if existing is None:
            raise FactorValueNotFoundError(value_id)
        await ensure_not_generating(self._jobs, table_id)

        if value is not None:
            if not value.strip():
                raise EmptyNameError("value")
            if any(v.value == value and v.id != existing.id for v in factor.values):
                raise DuplicateFactorValueError(value)
            existing.value = value
        if order_index is not None:
            existing.order_index = order_index

        await self._tables.save(table)
        return FactorValueRef(
            id=existing.id, value=existing.value, order_index=existing.order_index
        )

    async def delete_factor_value(
        self, table_id: int, factor_id: int, value_id: int
    ) -> None:
        table = await self._tables.get(table_id)
        if table is None:
            raise DecisionTableNotFoundError(table_id)
        factor = table.get_factor(factor_id)
        if factor is None:
            raise FactorNotFoundError(factor_id)
        value = factor.get_value(value_id)
        if value is None:
            raise FactorValueNotFoundError(value_id)
        await ensure_not_generating(self._jobs, table_id)

        factor.values = [v for v in factor.values if v.id != value.id]
        await self._tables.save(table)
        # Same rationale as delete_factor: invalidates every existing
        # combination's signature for this table.
        await self._combinations.delete_all_for_table(table_id)
        # Same rationale as delete_factor: a rule's assignment may
        # reference the deleted value (see spec 005).
        await self._rules.delete_all_for_table(table_id)
