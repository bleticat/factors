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
from app.shared.mediator.requests import Command
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


# --- Decision table ----------------------------------------------------


@dataclass(frozen=True)
class CreateDecisionTableCommand(Command[DecisionTableRef]):
    name: str
    description: str | None = None


class CreateDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: CreateDecisionTableCommand) -> DecisionTableRef:
        if not request.name.strip():
            raise EmptyNameError("name")
        table = await self._tables.add(
            DecisionTable(id=None, name=request.name, description=request.description)
        )
        assert table.id is not None
        return DecisionTableRef(id=table.id, name=table.name, description=table.description)


@dataclass(frozen=True)
class UpdateDecisionTableCommand(Command[DecisionTableRef]):
    table_id: int
    name: str | None = None
    description: str | None = None
    description_set: bool = False


class UpdateDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: UpdateDecisionTableCommand) -> DecisionTableRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        if request.name is not None:
            if not request.name.strip():
                raise EmptyNameError("name")
            table.name = request.name
        if request.description_set:
            table.description = request.description

        await self._tables.save(table)
        return DecisionTableRef(id=table.id, name=table.name, description=table.description)


@dataclass(frozen=True)
class DeleteDecisionTableCommand(Command[None]):
    table_id: int


class DeleteDecisionTableHandler:
    def __init__(self, tables: DecisionTableRepository) -> None:
        self._tables = tables

    async def handle(self, request: DeleteDecisionTableCommand) -> None:
        await self._tables.delete(request.table_id)


# --- Factors -------------------------------------------------------------


@dataclass(frozen=True)
class AddFactorCommand(Command[FactorRef]):
    table_id: int
    name: str


class AddFactorHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: AddFactorCommand) -> FactorRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        await ensure_not_generating(self._jobs, request.table_id)

        factor = table.add_factor(request.name)
        await self._tables.save(table)
        assert factor.id is not None
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)


@dataclass(frozen=True)
class UpdateFactorCommand(Command[FactorRef]):
    table_id: int
    factor_id: int
    name: str | None = None
    order_index: int | None = None


class UpdateFactorHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: UpdateFactorCommand) -> FactorRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        if request.name is not None:
            if not request.name.strip():
                raise EmptyNameError("name")
            if any(f.name == request.name and f.id != factor.id for f in table.factors):
                raise DuplicateFactorNameError(request.name)
            factor.name = request.name
        if request.order_index is not None:
            factor.order_index = request.order_index

        await self._tables.save(table)
        return FactorRef(id=factor.id, name=factor.name, order_index=factor.order_index)


@dataclass(frozen=True)
class DeleteFactorCommand(Command[None]):
    table_id: int
    factor_id: int


class DeleteFactorHandler:
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

    async def handle(self, request: DeleteFactorCommand) -> None:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        table.factors = [f for f in table.factors if f.id != factor.id]
        await self._tables.save(table)
        # Deleting a factor invalidates every existing combination's
        # signature (see spec 001) — cascade the whole set for this table.
        await self._combinations.delete_all_for_table(request.table_id)
        # A rule's assignment may reference the deleted factor; rather than
        # silently narrowing its meaning, invalidate every rule for this
        # table too (see spec 005).
        await self._rules.delete_all_for_table(request.table_id)


# --- Factor values ---------------------------------------------------------


@dataclass(frozen=True)
class AddFactorValueCommand(Command[FactorValueRef]):
    table_id: int
    factor_id: int
    value: str


class AddFactorValueHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: AddFactorValueCommand) -> FactorValueRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        await ensure_not_generating(self._jobs, request.table_id)

        value = factor.add_value(request.value)
        await self._tables.save(table)
        assert value.id is not None
        return FactorValueRef(id=value.id, value=value.value, order_index=value.order_index)


@dataclass(frozen=True)
class UpdateFactorValueCommand(Command[FactorValueRef]):
    table_id: int
    factor_id: int
    value_id: int
    value: str | None = None
    order_index: int | None = None


class UpdateFactorValueHandler:
    def __init__(self, tables: DecisionTableRepository, jobs: GenerationJobRepository) -> None:
        self._tables = tables
        self._jobs = jobs

    async def handle(self, request: UpdateFactorValueCommand) -> FactorValueRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        value = factor.get_value(request.value_id)
        if value is None:
            raise FactorValueNotFoundError(request.value_id)
        await ensure_not_generating(self._jobs, request.table_id)

        if request.value is not None:
            if not request.value.strip():
                raise EmptyNameError("value")
            if any(v.value == request.value and v.id != value.id for v in factor.values):
                raise DuplicateFactorValueError(request.value)
            value.value = request.value
        if request.order_index is not None:
            value.order_index = request.order_index

        await self._tables.save(table)
        return FactorValueRef(id=value.id, value=value.value, order_index=value.order_index)


@dataclass(frozen=True)
class DeleteFactorValueCommand(Command[None]):
    table_id: int
    factor_id: int
    value_id: int


class DeleteFactorValueHandler:
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

    async def handle(self, request: DeleteFactorValueCommand) -> None:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        factor = table.get_factor(request.factor_id)
        if factor is None:
            raise FactorNotFoundError(request.factor_id)
        value = factor.get_value(request.value_id)
        if value is None:
            raise FactorValueNotFoundError(request.value_id)
        await ensure_not_generating(self._jobs, request.table_id)

        factor.values = [v for v in factor.values if v.id != value.id]
        await self._tables.save(table)
        # Same rationale as DeleteFactorCommand: invalidates every existing
        # combination's signature for this table.
        await self._combinations.delete_all_for_table(request.table_id)
        # Same rationale as DeleteFactorCommand: a rule's assignment may
        # reference the deleted value (see spec 005).
        await self._rules.delete_all_for_table(request.table_id)
