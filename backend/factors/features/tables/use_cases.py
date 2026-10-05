from dataclasses import dataclass, field

from factors.features.tables.entities import DecisionTable, Factor, FactorValue
from factors.features.tables.ports.decision_table_reader import DecisionTableSummary
from factors.features.tables.service import ensure_not_generating
from factors.shared.errors import (
    InvariantViolationError,
    NotFoundError,
    ValidationError,
)
from factors.shared.pagination import Page, PageRequest
from factors.shared.ports.database import Database

# --- Requests/responses -------------------------------------------------


@dataclass(frozen=True)
class CreateDecisionTableRequest:
    name: str
    description: str | None = None


@dataclass(frozen=True)
class CreateDecisionTableResponse:
    table: DecisionTable


@dataclass(frozen=True)
class UpdateDecisionTableRequest:
    table_id: int
    name: str | None = None
    description: str | None = None
    description_set: bool = False


@dataclass(frozen=True)
class UpdateDecisionTableResponse:
    table: DecisionTable


@dataclass(frozen=True)
class DeleteDecisionTableRequest:
    table_id: int


@dataclass(frozen=True)
class AddFactorRequest:
    table_id: int
    name: str


@dataclass(frozen=True)
class AddFactorResponse:
    factor: Factor


@dataclass(frozen=True)
class UpdateFactorRequest:
    table_id: int
    factor_id: int
    name: str | None = None
    order_index: int | None = None


@dataclass(frozen=True)
class UpdateFactorResponse:
    factor: Factor


@dataclass(frozen=True)
class DeleteFactorRequest:
    table_id: int
    factor_id: int


@dataclass(frozen=True)
class AddFactorValueRequest:
    table_id: int
    factor_id: int
    value: str


@dataclass(frozen=True)
class AddFactorValueResponse:
    value: FactorValue


@dataclass(frozen=True)
class UpdateFactorValueRequest:
    table_id: int
    factor_id: int
    value_id: int
    value: str | None = None
    order_index: int | None = None


@dataclass(frozen=True)
class UpdateFactorValueResponse:
    value: FactorValue


@dataclass(frozen=True)
class DeleteFactorValueRequest:
    table_id: int
    factor_id: int
    value_id: int


@dataclass(frozen=True)
class GetDecisionTableRequest:
    table_id: int


@dataclass(frozen=True)
class GetDecisionTableResponse:
    table: DecisionTable


@dataclass(frozen=True)
class ListDecisionTablesRequest:
    page: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True)
class ListDecisionTablesResponse:
    page: Page[DecisionTableSummary]


@dataclass(frozen=True)
class ListFactorsRequest:
    table_id: int


@dataclass(frozen=True)
class ListFactorsResponse:
    factors: list[Factor]


class TablesUseCases:
    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Decision table ------------------------------------------------------

    async def create_decision_table(
        self, request: CreateDecisionTableRequest
    ) -> CreateDecisionTableResponse:
        if not request.name.strip():
            raise ValidationError("name must not be empty")
        async with self._database.transaction() as db:
            table = await db.tables.add(
                DecisionTable(
                    id=None, name=request.name, description=request.description
                )
            )
            return CreateDecisionTableResponse(table=table)

    async def update_decision_table(
        self, request: UpdateDecisionTableRequest
    ) -> UpdateDecisionTableResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            if request.name is not None:
                if not request.name.strip():
                    raise ValidationError("name must not be empty")
                table.name = request.name
            if request.description_set:
                table.description = request.description

            await db.tables.save(table)
            return UpdateDecisionTableResponse(table=table)

    async def delete_decision_table(self, request: DeleteDecisionTableRequest) -> None:
        async with self._database.transaction() as db:
            await db.tables.delete(request.table_id)

    # --- Factors --------------------------------------------------------------

    async def add_factor(self, request: AddFactorRequest) -> AddFactorResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            factor = table.add_factor(request.name)
            await db.tables.save(table)
            return AddFactorResponse(factor=factor)

    async def update_factor(self, request: UpdateFactorRequest) -> UpdateFactorResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            factor = table.get_factor(request.factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {request.factor_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            if request.name is not None:
                if not request.name.strip():
                    raise ValidationError("name must not be empty")
                if any(
                    f.name == request.name and f.id != factor.id for f in table.factors
                ):
                    raise InvariantViolationError(
                        f"Factor name {request.name!r} is already used in this table"
                    )
                factor.name = request.name
            if request.order_index is not None:
                factor.order_index = request.order_index

            await db.tables.save(table)
            return UpdateFactorResponse(factor=factor)

    async def delete_factor(self, request: DeleteFactorRequest) -> None:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            factor = table.get_factor(request.factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {request.factor_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            table.factors = [f for f in table.factors if f.id != factor.id]
            await db.tables.save(table)
            # Deleting a factor invalidates every existing combination's
            # signature (see spec 001) — cascade the whole set for this table.
            await db.combinations.delete_all_for_table(request.table_id)
            # A rule's assignment may reference the deleted factor; rather
            # than silently narrowing its meaning, invalidate every rule for
            # this table too (see spec 005).
            await db.rules.delete_all_for_table(request.table_id)

    # --- Factor values ----------------------------------------------------------

    async def add_factor_value(
        self, request: AddFactorValueRequest
    ) -> AddFactorValueResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            factor = table.get_factor(request.factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {request.factor_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            added = factor.add_value(request.value)
            await db.tables.save(table)
            return AddFactorValueResponse(value=added)

    async def update_factor_value(
        self, request: UpdateFactorValueRequest
    ) -> UpdateFactorValueResponse:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            factor = table.get_factor(request.factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {request.factor_id} not found")
            existing = factor.get_value(request.value_id)
            if existing is None:
                raise NotFoundError(f"Factor value {request.value_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            if request.value is not None:
                if not request.value.strip():
                    raise ValidationError("value must not be empty")
                if any(
                    v.value == request.value and v.id != existing.id
                    for v in factor.values
                ):
                    raise InvariantViolationError(
                        f"Value {request.value!r} is already used in this factor"
                    )
                existing.value = request.value
            if request.order_index is not None:
                existing.order_index = request.order_index

            await db.tables.save(table)
            return UpdateFactorValueResponse(value=existing)

    async def delete_factor_value(self, request: DeleteFactorValueRequest) -> None:
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            factor = table.get_factor(request.factor_id)
            if factor is None:
                raise NotFoundError(f"Factor {request.factor_id} not found")
            value = factor.get_value(request.value_id)
            if value is None:
                raise NotFoundError(f"Factor value {request.value_id} not found")
            await ensure_not_generating(db.jobs, request.table_id)

            factor.values = [v for v in factor.values if v.id != value.id]
            await db.tables.save(table)
            # Same rationale as delete_factor: invalidates every existing
            # combination's signature for this table.
            await db.combinations.delete_all_for_table(request.table_id)
            # Same rationale as delete_factor: a rule's assignment may
            # reference the deleted value (see spec 005).
            await db.rules.delete_all_for_table(request.table_id)

    # --- Reads ------------------------------------------------------------------

    async def get_decision_table(
        self, request: GetDecisionTableRequest
    ) -> GetDecisionTableResponse:
        async with self._database.snapshot() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            return GetDecisionTableResponse(table=table)

    async def list_decision_tables(
        self, request: ListDecisionTablesRequest = ListDecisionTablesRequest()
    ) -> ListDecisionTablesResponse:
        async with self._database.snapshot() as db:
            page = await db.tables_reader.list_summaries(request.page)
            return ListDecisionTablesResponse(page=page)

    async def list_factors(self, request: ListFactorsRequest) -> ListFactorsResponse:
        async with self._database.snapshot() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            return ListFactorsResponse(factors=table.factors)
