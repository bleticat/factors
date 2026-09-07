from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.decision_tables.adapters.orm import RuleRow, RuleValueRow
from app.decision_tables.domain.rule import Rule, RuleAssignment
from app.decision_tables.ports.rule_repository import RuleRepository
from app.shared.database.sqlalchemy_database import SqlAlchemyUnitOfWork


def _to_domain(row: RuleRow) -> Rule:
    return Rule(
        id=row.id,
        decision_table_id=row.decision_table_id,
        output=row.output,
        factor_values=[
            RuleAssignment(factor_id=v.factor_id, factor_value_id=v.factor_value_id) for v in row.values
        ],
        matched_count=row.matched_count,
        applied_at=row.applied_at,
    )


class SqlAlchemyRuleRepository(RuleRepository):
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._session: AsyncSession = uow.session

    async def add(self, rule: Rule) -> Rule:
        row = RuleRow(
            decision_table_id=rule.decision_table_id,
            output=rule.output,
            matched_count=rule.matched_count,
            applied_at=rule.applied_at,
        )
        self._session.add(row)
        await self._session.flush()

        value_rows = [
            RuleValueRow(rule_id=row.id, factor_id=a.factor_id, factor_value_id=a.factor_value_id)
            for a in rule.factor_values
        ]
        self._session.add_all(value_rows)
        await self._session.flush()

        return Rule(
            id=row.id,
            decision_table_id=row.decision_table_id,
            output=row.output,
            factor_values=list(rule.factor_values),
            matched_count=row.matched_count,
            applied_at=row.applied_at,
        )

    async def get(self, table_id: int, rule_id: int) -> Rule | None:
        stmt = (
            select(RuleRow)
            .where(RuleRow.id == rule_id, RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else _to_domain(row)

    async def list_for_table(self, table_id: int) -> list[Rule]:
        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(row) for row in rows]

    async def delete(self, table_id: int, rule_id: int) -> bool:
        stmt = delete(RuleRow).where(RuleRow.id == rule_id, RuleRow.decision_table_id == table_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return bool(result.rowcount)

    async def delete_all_for_table(self, table_id: int) -> None:
        stmt = delete(RuleRow).where(RuleRow.decision_table_id == table_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def record_apply(self, rule_id: int, matched_count: int, applied_at: datetime) -> None:
        row = await self._session.get(RuleRow, rule_id)
        assert row is not None
        row.matched_count = matched_count
        row.applied_at = applied_at
        await self._session.flush()
