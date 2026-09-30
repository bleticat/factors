"""Use cases for the `rules` module."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime

from app.combinations.ports.combination_queries import (
    CombinationOverlapDTO,
    RuleFilterInput,
)
from app.combinations.ports.combination_repository import FactorValueAssignment
from app.rules.entities import Rule, RuleAssignment
from app.rules.errors import InvalidRuleOrderError
from app.rules.ports.rule_queries import RuleDTO
from app.rules.service import RuleApplyRef, apply_rule
from app.shared.errors import (
    DuplicateFactorInAssignmentError,
    EmptyNameError,
    NotFoundError,
)
from app.shared.pagination import Page, PageRequest
from app.shared.ports.database import Database


@dataclass(frozen=True)
class RuleRef:
    id: int
    matched_count: int
    applied_at: datetime | None


@dataclass(frozen=True)
class ReapplyRulesResult:
    results: list[RuleApplyRef]


class RulesUseCases:
    """The `rules` module's use cases, one method each. Constructed once
    with the app's `Database`."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def create_rule(
        self,
        table_id: int,
        factor_values: tuple[tuple[int, int], ...] = (),
        output: str = "",
        title: str | None = None,
    ) -> RuleRef:
        """Create a new rule for a decision table and immediately apply it
        to the table's current combinations (spec 005).

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            EmptyNameError: if `output` is blank.
            DuplicateFactorInAssignmentError: if `factor_values` names the
                same factor twice.
            UnknownFactorInFilterError: if `factor_values` names a factor not
                on this table.
            UnknownFactorValueInFilterError: if `factor_values` names a value
                not on that factor.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            if not output.strip():
                raise EmptyNameError("output")

            seen: set[int] = set()
            for factor_id, _ in factor_values:
                if factor_id in seen:
                    raise DuplicateFactorInAssignmentError(factor_id)
                seen.add(factor_id)
            table.validate_factor_value_pairs(list(factor_values))

            new_factor_values = [
                RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in factor_values
            ]
            existing_rules = await uow.rules.list_for_table(table_id)

            clean_title = title.strip() if title and title.strip() else None
            rule = Rule(
                id=None,
                decision_table_id=table_id,
                output=output,
                title=clean_title,
                order_index=len(
                    existing_rules
                ),  # append at the end (spec 008); drag to reorder afterward
                factor_values=new_factor_values,
            )
            rule = await uow.rules.add(rule)

            applied = await apply_rule(uow.combinations, uow.rules, rule)
            return RuleRef(
                id=applied.rule_id,
                matched_count=applied.matched_count,
                applied_at=applied.applied_at,
            )

    async def update_rule(
        self,
        table_id: int,
        rule_id: int,
        output: str | None = None,
        title: str | None = None,
        title_set: bool = False,
        factor_values: tuple[tuple[int, int], ...] | None = None,
        factor_values_set: bool = False,
    ) -> RuleRef:
        """Edits an existing rule's output/title/assignment in place, without
        changing its position (`order_index`) — see spec 008/009. Reordering is
        a separate use case (`reorder_rules`), done from the "Saved rules"
        list; any assignment is allowed regardless of how general it is
        relative to other rules (spec 009) — a rule shadowed by a later, more
        general one is the user's call to notice and fix (surfaced via
        `list_rule_overlaps`/`list_rules`' `shadowed_count`), not something
        the backend blocks.

        Raises:
            NotFoundError: if `table_id` or `rule_id` doesn't exist.
            EmptyNameError: if `output` is given but blank.
            DuplicateFactorInAssignmentError: if `factor_values` names the
                same factor twice.
            UnknownFactorInFilterError: if `factor_values` names a factor not
                on this table.
            UnknownFactorValueInFilterError: if `factor_values` names a value
                not on that factor.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")
            rule = await uow.rules.get(table_id, rule_id)
            if rule is None:
                raise NotFoundError(f"Rule {rule_id} not found")

            if output is not None:
                if not output.strip():
                    raise EmptyNameError("output")
                rule.output = output
            if title_set:
                rule.title = title.strip() if title and title.strip() else None

            if factor_values_set:
                assert factor_values is not None
                seen: set[int] = set()
                for factor_id, _ in factor_values:
                    if factor_id in seen:
                        raise DuplicateFactorInAssignmentError(factor_id)
                    seen.add(factor_id)
                table.validate_factor_value_pairs(list(factor_values))
                rule.factor_values = [
                    RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                    for factor_id, factor_value_id in factor_values
                ]

            await uow.rules.save(rule)

            if factor_values_set or output is not None:
                applied = await apply_rule(uow.combinations, uow.rules, rule)
                return RuleRef(
                    id=applied.rule_id,
                    matched_count=applied.matched_count,
                    applied_at=applied.applied_at,
                )
            return RuleRef(
                id=rule.id, matched_count=rule.matched_count, applied_at=rule.applied_at
            )

    async def delete_rule(self, table_id: int, rule_id: int) -> None:
        """Delete a rule. Combinations it last patched keep their current
        status/output (see spec 005's "no revert on delete").

        Raises:
            NotFoundError: if `table_id` or `rule_id` doesn't exist.
        """
        async with self._database.unit_of_work() as uow:
            # Deleting a rule leaves whatever status/output it last set on
            # combinations untouched — see spec 005's "no revert on delete".
            deleted = await uow.rules.delete(table_id, rule_id)
            if not deleted:
                raise NotFoundError(f"Rule {rule_id} not found")

    async def reorder_rules(
        self, table_id: int, ordered_rule_ids: tuple[int, ...] = ()
    ) -> ReapplyRulesResult:
        """Persists a complete new rule order for a table and immediately
        replays every rule in that order (spec 008) — a reorder is a
        permutation of the table's existing rule ids. Any order is allowed
        (spec 009): a rule that ends up shadowed by a later, more general
        one is the user's call to notice (surfaced via `shadowed_count`/
        `list_rule_overlaps`) and fix by dragging it further down, not
        something the backend rejects.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            InvalidRuleOrderError: if `ordered_rule_ids` isn't a permutation
                of the table's existing rule ids.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")

            existing = await uow.rules.list_for_table(table_id)
            requested_ids = list(ordered_rule_ids)
            if len(requested_ids) != len(set(requested_ids)) or set(requested_ids) != {
                r.id for r in existing
            }:
                raise InvalidRuleOrderError(table_id)

            by_id = {r.id: r for r in existing}
            for position, rid in enumerate(requested_ids):
                by_id[rid].order_index = position
                await uow.rules.save(by_id[rid])

            results = [
                await apply_rule(uow.combinations, uow.rules, by_id[rid])
                for rid in requested_ids
            ]
            return ReapplyRulesResult(results=results)

    async def reapply_rules(self, table_id: int) -> ReapplyRulesResult:
        """Replays every rule for a table against its current combinations,
        in creation order, so a later rule's output wins on any row both it
        and an earlier rule match (see spec 005). Invoked automatically by
        the generation worker once a job reaches `completed`, and exposed
        for on-demand use. Bounded by the table's rule count (not by
        combination count), so — unlike generation — it fits in a single
        transaction without batching.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        async with self._database.unit_of_work() as uow:
            table = await uow.tables.get(table_id)
            if table is None:
                raise NotFoundError(f"Decision table {table_id} not found")

            rules = await uow.rules.list_for_table(table_id)
            results = [
                await apply_rule(uow.combinations, uow.rules, rule) for rule in rules
            ]
            return ReapplyRulesResult(results=results)

    # --- Reads ------------------------------------------------------------------

    async def list_rules(
        self, table_id: int, page: PageRequest = PageRequest()
    ) -> Page[RuleDTO]:
        """List a decision table's rules, each tagged with how many of its
        matched combinations are currently shadowed by a later rule (spec 009).

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise NotFoundError(f"Decision table {table_id} not found")

        result = await self._database.rules_queries.list_for_table(table_id, page)
        if not result.items:
            return result

        # Shadowing (spec 009) depends on every rule's position/assignment,
        # not just this page's — a rule on this page can be shadowed by one
        # that lives on a different page.
        all_rules = await self._database.rules_queries.list_all_for_table(
            table_id
        )  # order_index order
        rule_inputs = [
            RuleFilterInput(
                rule_id=r.id,
                output=r.output,
                title=r.title,
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=fv.factor_id, factor_value_id=fv.factor_value_id
                    )
                    for fv in r.factor_values
                ),
            )
            for r in all_rules
        ]
        shadowed_counts = (
            await self._database.combinations_queries.count_shadowed_matches(
                table_id, rule_inputs
            )
        )
        if not shadowed_counts:
            return result

        items = [
            dataclasses.replace(rule, shadowed_count=shadowed_counts.get(rule.id, 0))
            for rule in result.items
        ]
        return Page(
            items=items, total=result.total, limit=result.limit, offset=result.offset
        )

    async def list_rule_overlaps(
        self, table_id: int, page: PageRequest = PageRequest()
    ) -> Page[CombinationOverlapDTO]:
        """See spec 006: rows matched by 2+ of the table's current rules,
        tagged with which rules matched and (last in id order) which one
        currently wins a reapply.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        table = await self._database.tables_queries.get(table_id)
        if table is None:
            raise NotFoundError(f"Decision table {table_id} not found")

        rules = await self._database.rules_queries.list_all_for_table(table_id)
        rule_inputs = [
            RuleFilterInput(
                rule_id=rule.id,
                output=rule.output,
                title=rule.title,
                factor_values=tuple(
                    FactorValueAssignment(
                        factor_id=fv.factor_id, factor_value_id=fv.factor_value_id
                    )
                    for fv in rule.factor_values
                ),
            )
            for rule in rules
        ]
        return await self._database.combinations_queries.list_matched_by_multiple_rules(
            table_id, rule_inputs, page
        )
