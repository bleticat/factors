from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.shared.pagination import Page, PageRequest
from app.tables.adapters.orm import DecisionTableRow, FactorRow
from app.tables.ports.decision_table_queries import (
    DecisionTableDTO,
    DecisionTableQueries,
    DecisionTableSummaryDTO,
    FactorDTO,
    FactorValueDTO,
)


class SqlAlchemyDecisionTableQueries(DecisionTableQueries):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, table_id: int) -> DecisionTableDTO | None:
        """Return a decision table with its factors and values, or None if
        `table_id` doesn't exist."""
        async with self._session_factory() as session:
            stmt = (
                select(DecisionTableRow)
                .where(DecisionTableRow.id == table_id)
                .options(
                    selectinload(DecisionTableRow.factors).selectinload(
                        FactorRow.values
                    )
                )
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            return DecisionTableDTO(
                id=row.id,
                name=row.name,
                description=row.description,
                factors=[
                    FactorDTO(
                        id=f.id,
                        name=f.name,
                        order_index=f.order_index,
                        values=[
                            FactorValueDTO(
                                id=v.id, value=v.value, order_index=v.order_index
                            )
                            for v in f.values
                        ],
                    )
                    for f in row.factors
                ],
            )

    async def list_summaries(self, page: PageRequest) -> Page[DecisionTableSummaryDTO]:
        """Return a page of decision table summaries, most recently created first."""
        async with self._session_factory() as session:
            total = (
                await session.execute(
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
                .order_by(
                    DecisionTableRow.created_at.desc(), DecisionTableRow.id.desc()
                )
                .limit(page.limit)
                .offset(page.offset)
            )
            rows = (await session.execute(stmt)).scalars().all()
            items = [
                DecisionTableSummaryDTO(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    factor_count=len(row.factors),
                )
                for row in rows
            ]
            return Page(items=items, total=total, limit=page.limit, offset=page.offset)
