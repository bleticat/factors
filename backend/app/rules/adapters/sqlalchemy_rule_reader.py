from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.rules.adapters.orm import RuleRow
from app.rules.ports.rule_reader import RuleDTO, RuleReader, RuleValueDTO
from app.shared.pagination import Page, PageRequest


def _to_dto(row: RuleRow) -> RuleDTO:
    return RuleDTO(
        id=row.id,
        decision_table_id=row.decision_table_id,
        output=row.output,
        title=row.title,
        order_index=row.order_index,
        factor_values=[
            RuleValueDTO(factor_id=v.factor_id, factor_value_id=v.factor_value_id)
            for v in row.values
        ],
        matched_count=row.matched_count,
        applied_at=row.applied_at,
        created_at=row.created_at,
    )


class SqlAlchemyRuleReader(RuleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[RuleDTO]:
        """Return a page of a decision table's rules, ordered by `order_index`."""
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
            items=[_to_dto(row) for row in rows],
            total=total,
            limit=page.limit,
            offset=page.offset,
        )

    async def list_all_for_table(self, table_id: int) -> list[RuleDTO]:
        """Unpaginated, ordered by `order_index` — the same order rules are
        (re)applied in (spec 008; was creation/id order before it). Used by
        `list_rule_overlaps`, which needs every rule's assignment to compute
        overlaps, not one page."""
        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.order_index, RuleRow.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_dto(row) for row in rows]

    async def get(self, table_id: int, rule_id: int) -> RuleDTO | None:
        """Return one rule, or None if it doesn't exist on this table."""
        stmt = (
            select(RuleRow)
            .where(RuleRow.id == rule_id, RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else _to_dto(row)
