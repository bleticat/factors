from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.pagination import Page, PageRequest
from app.tables.adapters.orm import DecisionTableRow
from app.tables.ports.decision_table_reader import (
    DecisionTableReader,
    DecisionTableSummary,
)


class SqlAlchemyDecisionTableReader(DecisionTableReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_summaries(self, page: PageRequest) -> Page[DecisionTableSummary]:
        """Return a page of decision table summaries, most recently created first."""
        total = (
            await self._session.execute(
                select(func.count()).select_from(DecisionTableRow)
            )
        ).scalar_one()

        stmt = (
            select(DecisionTableRow)
            .options(selectinload(DecisionTableRow.factors))
            # SQLite's CURRENT_TIMESTAMP default has only second
            # resolution, so rows created within the same second tie on
            # created_at — break ties by id (higher id = created later)
            # to keep "most recently created first" well-defined.
            .order_by(DecisionTableRow.created_at.desc(), DecisionTableRow.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        items = [
            DecisionTableSummary(
                id=row.id,
                name=row.name,
                description=row.description,
                factor_count=len(row.factors),
            )
            for row in rows
        ]
        return Page(items=items, total=total, limit=page.limit, offset=page.offset)
