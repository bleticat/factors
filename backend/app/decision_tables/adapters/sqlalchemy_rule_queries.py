from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.decision_tables.adapters.orm import RuleRow
from app.decision_tables.ports.rule_queries import RuleDTO, RuleQueries, RuleValueDTO
from app.shared.database.sqlalchemy_database import SqlAlchemyReadScope
from app.shared.pagination import Page, PageRequest


def _to_dto(row: RuleRow) -> RuleDTO:
    return RuleDTO(
        id=row.id,
        decision_table_id=row.decision_table_id,
        output=row.output,
        title=row.title,
        order_index=row.order_index,
        factor_values=[
            RuleValueDTO(factor_id=v.factor_id, factor_value_id=v.factor_value_id) for v in row.values
        ],
        matched_count=row.matched_count,
        applied_at=row.applied_at,
        created_at=row.created_at,
    )


class SqlAlchemyRuleQueries(RuleQueries):
    def __init__(self, scope: SqlAlchemyReadScope) -> None:
        self._session: AsyncSession = scope.session

    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[RuleDTO]:
        count_stmt = select(func.count(RuleRow.id)).where(RuleRow.decision_table_id == table_id)
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.order_index, RuleRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return Page(items=[_to_dto(row) for row in rows], total=total, limit=page.limit, offset=page.offset)

    async def list_all_for_table(self, table_id: int) -> list[RuleDTO]:
        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.order_index, RuleRow.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_dto(row) for row in rows]

    async def get(self, table_id: int, rule_id: int) -> RuleDTO | None:
        stmt = (
            select(RuleRow)
            .where(RuleRow.id == rule_id, RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else _to_dto(row)
