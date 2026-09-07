from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.decision_tables.adapters.combination_filters import apply_combination_filter
from app.decision_tables.adapters.orm import CombinationRow
from app.decision_tables.ports.combination_queries import (
    CombinationDTO,
    CombinationQueries,
    CombinationValueDTO,
)
from app.decision_tables.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
from app.shared.database.sqlalchemy_database import SqlAlchemyReadScope
from app.shared.pagination import Page, PageRequest


def _to_dto(row: CombinationRow) -> CombinationDTO:
    return CombinationDTO(
        id=row.id,
        decision_table_id=row.decision_table_id,
        status=row.status,
        output=row.output,
        impossible_reason=row.impossible_reason,
        values=[
            CombinationValueDTO(factor_id=v.factor_id, factor_value_id=v.factor_value_id)
            for v in row.values
        ],
    )


class SqlAlchemyCombinationQueries(CombinationQueries):
    def __init__(self, scope: SqlAlchemyReadScope) -> None:
        self._session: AsyncSession = scope.session

    async def list_(
        self, table_id: int, filter_: CombinationFilter, page: PageRequest
    ) -> Page[CombinationDTO]:
        count_stmt = apply_combination_filter(
            select(func.count(CombinationRow.id.distinct())), table_id, filter_
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = apply_combination_filter(select(CombinationRow), table_id, filter_)
        stmt = (
            stmt.options(selectinload(CombinationRow.values))
            .order_by(CombinationRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return Page(
            items=[_to_dto(row) for row in rows], total=total, limit=page.limit, offset=page.offset
        )

    async def get(self, table_id: int, combination_id: int) -> CombinationDTO | None:
        stmt = (
            select(CombinationRow)
            .where(CombinationRow.id == combination_id, CombinationRow.decision_table_id == table_id)
            .options(selectinload(CombinationRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else _to_dto(row)

    async def find_by_exact_assignment(
        self, table_id: int, assignment: list[tuple[int, int]]
    ) -> CombinationDTO | None:
        filter_ = CombinationFilter(
            factor_values=tuple(
                FactorValueAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in assignment
            )
        )
        stmt = apply_combination_filter(select(CombinationRow), table_id, filter_).options(
            selectinload(CombinationRow.values)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else _to_dto(row)
