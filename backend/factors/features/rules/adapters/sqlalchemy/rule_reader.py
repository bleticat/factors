from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from factors.features.rules.adapters.sqlalchemy.orm import RuleRow
from factors.features.rules.adapters.sqlalchemy.rule_repository import row_to_rule
from factors.features.rules.entities import Rule
from factors.features.rules.ports.rule_reader import RuleReader
from factors.shared.pagination import Page, PageRequest


class SqlAlchemyRuleReader(RuleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[Rule]:
        count_stmt = select(func.count(RuleRow.id)).where(
            RuleRow.decision_table_id == table_id
        )
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
        return Page(
            items=[row_to_rule(row) for row in rows],
            total=total,
            limit=page.limit,
            offset=page.offset,
        )

    async def list_all_for_table(self, table_id: int) -> list[Rule]:
        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.order_index, RuleRow.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [row_to_rule(row) for row in rows]
