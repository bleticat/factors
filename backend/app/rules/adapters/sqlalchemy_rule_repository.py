from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.rules.adapters.orm import RuleRow, RuleValueRow
from app.rules.entities import Rule, RuleAssignment
from app.rules.ports.rule_repository import RuleRepository


def row_to_rule(row: RuleRow) -> Rule:
    return Rule(
        id=row.id,
        decision_table_id=row.decision_table_id,
        output=row.output,
        title=row.title,
        order_index=row.order_index,
        factor_values=[
            RuleAssignment(factor_id=v.factor_id, factor_value_id=v.factor_value_id)
            for v in row.values
        ],
        matched_count=row.matched_count,
        applied_at=row.applied_at,
        created_at=row.created_at,
    )


class SqlAlchemyRuleRepository(RuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, rule: Rule) -> Rule:
        row = RuleRow(
            decision_table_id=rule.decision_table_id,
            output=rule.output,
            title=rule.title,
            order_index=rule.order_index,
            matched_count=rule.matched_count,
            applied_at=rule.applied_at,
        )
        self._session.add(row)
        await self._session.flush()

        value_rows = [
            RuleValueRow(
                rule_id=row.id, factor_id=a.factor_id, factor_value_id=a.factor_value_id
            )
            for a in rule.factor_values
        ]
        self._session.add_all(value_rows)
        await self._session.flush()

        return Rule(
            id=row.id,
            decision_table_id=row.decision_table_id,
            output=row.output,
            title=row.title,
            order_index=row.order_index,
            factor_values=list(rule.factor_values),
            matched_count=row.matched_count,
            applied_at=row.applied_at,
            created_at=row.created_at,
        )

    async def save(self, rule: Rule) -> None:
        assert rule.id is not None
        row = await self._session.get(RuleRow, rule.id)
        assert row is not None
        row.output = rule.output
        row.title = rule.title
        row.order_index = rule.order_index

        await self._session.execute(
            delete(RuleValueRow).where(RuleValueRow.rule_id == rule.id)
        )
        self._session.add_all(
            [
                RuleValueRow(
                    rule_id=rule.id,
                    factor_id=a.factor_id,
                    factor_value_id=a.factor_value_id,
                )
                for a in rule.factor_values
            ]
        )
        await self._session.flush()

    async def get(self, table_id: int, rule_id: int) -> Rule | None:
        stmt = (
            select(RuleRow)
            .where(RuleRow.id == rule_id, RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else row_to_rule(row)

    async def list_for_table(self, table_id: int) -> list[Rule]:
        stmt = (
            select(RuleRow)
            .where(RuleRow.decision_table_id == table_id)
            .options(selectinload(RuleRow.values))
            .order_by(RuleRow.order_index, RuleRow.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [row_to_rule(row) for row in rows]

    async def delete(self, table_id: int, rule_id: int) -> bool:
        stmt = delete(RuleRow).where(
            RuleRow.id == rule_id, RuleRow.decision_table_id == table_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return bool(result.rowcount)

    async def delete_all_for_table(self, table_id: int) -> None:
        stmt = delete(RuleRow).where(RuleRow.decision_table_id == table_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def record_apply(
        self, rule_id: int, matched_count: int, applied_at: datetime
    ) -> None:
        row = await self._session.get(RuleRow, rule_id)
        assert row is not None
        row.matched_count = matched_count
        row.applied_at = applied_at
        await self._session.flush()
