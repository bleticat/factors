from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.tables.adapters.orm import DecisionTableRow, FactorRow, FactorValueRow
from app.tables.entities import DecisionTable, Factor, FactorValue
from app.tables.ports.decision_table_repository import DecisionTableRepository


def _to_domain(row: DecisionTableRow) -> DecisionTable:
    return DecisionTable(
        id=row.id,
        name=row.name,
        description=row.description,
        factors=[
            Factor(
                id=factor_row.id,
                name=factor_row.name,
                order_index=factor_row.order_index,
                values=[
                    FactorValue(id=v.id, value=v.value, order_index=v.order_index)
                    for v in factor_row.values
                ],
            )
            for factor_row in row.factors
        ],
    )


class SqlAlchemyDecisionTableRepository(DecisionTableRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, table: DecisionTable) -> DecisionTable:
        row = DecisionTableRow(name=table.name, description=table.description)
        self._session.add(row)
        await self._session.flush()
        table.id = row.id
        return table

    async def get(self, table_id: int) -> DecisionTable | None:
        row = await self._load_row(table_id)
        return None if row is None else _to_domain(row)

    async def save(self, table: DecisionTable) -> None:
        assert table.id is not None
        row = await self._load_row(table.id)
        assert row is not None

        row.name = table.name
        row.description = table.description

        existing_factors = {f.id: f for f in row.factors}
        seen_factor_ids: set[int] = set()

        for factor in table.factors:
            if factor.id is None:
                factor_row = FactorRow(
                    decision_table_id=table.id,
                    name=factor.name,
                    order_index=factor.order_index,
                )
                self._session.add(factor_row)
                await self._session.flush()
                factor.id = factor_row.id
                existing_values: dict[int, FactorValueRow] = {}
            else:
                factor_row = existing_factors[factor.id]
                factor_row.name = factor.name
                factor_row.order_index = factor.order_index
                seen_factor_ids.add(factor.id)
                existing_values = {v.id: v for v in factor_row.values}

            seen_value_ids: set[int] = set()
            for value in factor.values:
                if value.id is None:
                    value_row = FactorValueRow(
                        factor_id=factor_row.id,
                        value=value.value,
                        order_index=value.order_index,
                    )
                    self._session.add(value_row)
                    await self._session.flush()
                    value.id = value_row.id
                else:
                    value_row = existing_values[value.id]
                    value_row.value = value.value
                    value_row.order_index = value.order_index
                    seen_value_ids.add(value.id)

            for value_id, value_row in existing_values.items():
                if value_id not in seen_value_ids:
                    await self._session.delete(value_row)

        for factor_id, factor_row in existing_factors.items():
            if factor_id not in seen_factor_ids:
                await self._session.delete(factor_row)

        await self._session.flush()

    async def delete(self, table_id: int) -> None:
        row = await self._session.get(DecisionTableRow, table_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def _load_row(self, table_id: int) -> DecisionTableRow | None:
        stmt = (
            select(DecisionTableRow)
            .where(DecisionTableRow.id == table_id)
            .options(
                selectinload(DecisionTableRow.factors).selectinload(FactorRow.values)
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
