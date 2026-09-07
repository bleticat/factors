from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.decision_tables.adapters.combination_filters import apply_combination_filter
from app.decision_tables.adapters.orm import CombinationRow
from app.decision_tables.ports.combination_queries import (
    CombinationDTO,
    CombinationOverlapDTO,
    CombinationQueries,
    CombinationValueDTO,
    RuleFilterInput,
    RuleTagDTO,
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

    async def list_matched_by_multiple_rules(
        self, table_id: int, rules: list[RuleFilterInput], page: PageRequest
    ) -> Page[CombinationOverlapDTO]:
        if len(rules) < 2:
            return Page(items=[], total=0, limit=page.limit, offset=page.offset)

        # One SELECT per rule, tagging each of its matching combination ids
        # with the rule's id, then unioned so a combination matched by
        # several rules appears once per matching rule.
        per_rule_matches = [
            apply_combination_filter(
                select(
                    literal(rule.rule_id).label("rule_id"),
                    CombinationRow.id.label("combination_id"),
                ),
                table_id,
                CombinationFilter(factor_values=rule.factor_values),
            )
            for rule in rules
        ]
        matches = union_all(*per_rule_matches).subquery("rule_matches")

        overlap_ids = (
            select(matches.c.combination_id)
            .group_by(matches.c.combination_id)
            .having(func.count(func.distinct(matches.c.rule_id)) >= 2)
        )
        total = (
            await self._session.execute(select(func.count()).select_from(overlap_ids.subquery()))
        ).scalar_one()

        page_ids = [
            row[0]
            for row in (
                await self._session.execute(
                    overlap_ids.order_by(matches.c.combination_id).limit(page.limit).offset(page.offset)
                )
            ).all()
        ]
        if not page_ids:
            return Page(items=[], total=total, limit=page.limit, offset=page.offset)

        combo_rows = (
            await self._session.execute(
                select(CombinationRow)
                .where(CombinationRow.id.in_(page_ids))
                .options(selectinload(CombinationRow.values))
            )
        ).scalars().all()
        combos_by_id = {row.id: _to_dto(row) for row in combo_rows}

        matching_rule_ids: dict[int, list[int]] = defaultdict(list)
        tag_rows = await self._session.execute(
            select(matches.c.combination_id, matches.c.rule_id).where(
                matches.c.combination_id.in_(page_ids)
            )
        )
        for combination_id, rule_id in tag_rows:
            matching_rule_ids[combination_id].append(rule_id)

        rules_by_id = {rule.rule_id: rule for rule in rules}
        items = [
            CombinationOverlapDTO(
                combination=combos_by_id[combination_id],
                matching_rules=[
                    RuleTagDTO(
                        id=rule_id,
                        output=rules_by_id[rule_id].output,
                        title=rules_by_id[rule_id].title,
                    )
                    for rule_id in sorted(set(matching_rule_ids[combination_id]))
                ],
            )
            for combination_id in page_ids  # already ordered by combination id
        ]
        return Page(items=items, total=total, limit=page.limit, offset=page.offset)
