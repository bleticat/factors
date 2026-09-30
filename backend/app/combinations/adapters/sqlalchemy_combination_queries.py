from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.combinations.adapters.combination_filters import apply_combination_filter
from app.combinations.adapters.orm import CombinationRow
from app.combinations.ports.combination_queries import (
    CombinationDTO,
    CombinationOverlapDTO,
    CombinationQueries,
    CombinationValueDTO,
    RuleFilterInput,
    RuleTagDTO,
)
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    FactorValueAssignment,
)
from app.shared.pagination import Page, PageRequest


def _to_dto(row: CombinationRow) -> CombinationDTO:
    return CombinationDTO(
        id=row.id,
        decision_table_id=row.decision_table_id,
        status=row.status,
        output=row.output,
        impossible_reason=row.impossible_reason,
        values=[
            CombinationValueDTO(
                factor_id=v.factor_id, factor_value_id=v.factor_value_id
            )
            for v in row.values
        ],
    )


class SqlAlchemyCombinationQueries(CombinationQueries):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_(
        self, table_id: int, filter_: CombinationFilter, page: PageRequest
    ) -> Page[CombinationDTO]:
        """Return a page of a decision table's combinations matching `filter_`."""
        async with self._session_factory() as session:
            count_stmt = apply_combination_filter(
                select(func.count(CombinationRow.id.distinct())), table_id, filter_
            )
            total = (await session.execute(count_stmt)).scalar_one()

            stmt = apply_combination_filter(select(CombinationRow), table_id, filter_)
            stmt = (
                stmt.options(selectinload(CombinationRow.values))
                .order_by(CombinationRow.id)
                .limit(page.limit)
                .offset(page.offset)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return Page(
                items=[_to_dto(row) for row in rows],
                total=total,
                limit=page.limit,
                offset=page.offset,
            )

    async def get(self, table_id: int, combination_id: int) -> CombinationDTO | None:
        """Return one combination, or None if it doesn't exist on this table."""
        async with self._session_factory() as session:
            stmt = (
                select(CombinationRow)
                .where(
                    CombinationRow.id == combination_id,
                    CombinationRow.decision_table_id == table_id,
                )
                .options(selectinload(CombinationRow.values))
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return None if row is None else _to_dto(row)

    async def find_by_exact_assignment(
        self, table_id: int, assignment: list[tuple[int, int]]
    ) -> CombinationDTO | None:
        """Full-assignment evaluate: the assignment covers every factor of
        the table, so at most one combination can match."""
        async with self._session_factory() as session:
            filter_ = CombinationFilter(
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=factor_id, factor_value_id=factor_value_id
                    )
                    for factor_id, factor_value_id in assignment
                )
            )
            stmt = apply_combination_filter(
                select(CombinationRow), table_id, filter_
            ).options(selectinload(CombinationRow.values))
            row = (await session.execute(stmt)).scalar_one_or_none()
            return None if row is None else _to_dto(row)

    async def list_matched_by_multiple_rules(
        self, table_id: int, rules: list[RuleFilterInput], page: PageRequest
    ) -> Page[CombinationOverlapDTO]:
        """Rows matched by 2+ of the given rules' assignments (spec 006).
        Callers pass every rule for the table; a caller passing fewer than
        two rules gets an empty page back."""
        if len(rules) < 2:
            return Page(items=[], total=0, limit=page.limit, offset=page.offset)

        async with self._session_factory() as session:
            # One SELECT per rule, tagging each of its matching combination
            # ids with the rule's id, then unioned so a combination matched
            # by several rules appears once per matching rule.
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
                await session.execute(
                    select(func.count()).select_from(overlap_ids.subquery())
                )
            ).scalar_one()

            page_ids = [
                row[0]
                for row in (
                    await session.execute(
                        overlap_ids.order_by(matches.c.combination_id)
                        .limit(page.limit)
                        .offset(page.offset)
                    )
                ).all()
            ]
            if not page_ids:
                return Page(items=[], total=total, limit=page.limit, offset=page.offset)

            combo_rows = (
                (
                    await session.execute(
                        select(CombinationRow)
                        .where(CombinationRow.id.in_(page_ids))
                        .options(selectinload(CombinationRow.values))
                    )
                )
                .scalars()
                .all()
            )
            combos_by_id = {row.id: _to_dto(row) for row in combo_rows}

            matching_rule_ids: dict[int, set[int]] = defaultdict(set)
            tag_rows = await session.execute(
                select(matches.c.combination_id, matches.c.rule_id).where(
                    matches.c.combination_id.in_(page_ids)
                )
            )
            for combination_id, rule_id in tag_rows:
                matching_rule_ids[combination_id].add(rule_id)

            # `rules` is given in apply order (spec 008's order_index, not
            # rule id) — sort each row's tags by *that* order so the last
            # one shown is always the rule that actually wins after a
            # reapply, even after rules have been reordered.
            rules_by_id = {rule.rule_id: rule for rule in rules}
            apply_position = {
                rule.rule_id: position for position, rule in enumerate(rules)
            }
            items = [
                CombinationOverlapDTO(
                    combination=combos_by_id[combination_id],
                    matching_rules=[
                        RuleTagDTO(
                            id=rule_id,
                            output=rules_by_id[rule_id].output,
                            title=rules_by_id[rule_id].title,
                        )
                        for rule_id in sorted(
                            matching_rule_ids[combination_id], key=apply_position.get
                        )
                    ],
                )
                for combination_id in page_ids  # already ordered by combination id
            ]
            return Page(items=items, total=total, limit=page.limit, offset=page.offset)

    async def count_shadowed_matches(
        self, table_id: int, ordered_rules: list[RuleFilterInput]
    ) -> dict[int, int]:
        """Spec 009: rules are no longer prevented from being more general
        than one another, so a rule can end up **shadowed** — some or all of
        the rows it matches are also matched by a rule later in `ordered_rules`
        (list order = apply order), whose output wins instead after a
        reapply. Returns `{rule_id: shadowed_count}` — how many of that
        rule's own matched rows currently show a *different* rule's output,
        for every rule that has at least one such row (a rule with none is
        simply absent from the result, not present with 0)."""
        if len(ordered_rules) < 2:
            return {}

        async with self._session_factory() as session:
            # Same per-rule tagged match set as
            # `list_matched_by_multiple_rules`, but tagged with position
            # (apply order) instead of rule id, so a later-position match
            # can be detected with a plain `>` comparison.
            per_rule_matches = [
                apply_combination_filter(
                    select(
                        literal(rule.rule_id).label("rule_id"),
                        literal(position).label("position"),
                        CombinationRow.id.label("combination_id"),
                    ),
                    table_id,
                    CombinationFilter(factor_values=rule.factor_values),
                )
                for position, rule in enumerate(ordered_rules)
            ]
            matches = union_all(*per_rule_matches).subquery("shadow_matches")
            later = matches.alias("later_matches")

            stmt = (
                select(
                    matches.c.rule_id,
                    func.count(func.distinct(matches.c.combination_id)),
                )
                .select_from(matches)
                .join(
                    later,
                    (later.c.combination_id == matches.c.combination_id)
                    & (later.c.position > matches.c.position),
                )
                .group_by(matches.c.rule_id)
            )
            rows = await session.execute(stmt)
            return dict(rows.all())
