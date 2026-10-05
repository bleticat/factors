"""Use cases for the `rules` module. Every public method takes one
`...Request` and returns one `...Response` wrapping the real `Rule`
entity/entities straight from the repository/reader — there is no
separate "DTO"/"Ref" type mirroring a `Rule`'s fields; see `entities.py`
for how `created_at`/`shadowed_count` ended up on the entity itself rather
than on a read-only shadow of it.
"""

import dataclasses
from dataclasses import dataclass, field

from app.combinations.ports.combination_reader import (
    CombinationOverlap,
    RuleFilterInput,
)
from app.combinations.ports.combination_repository import FactorValueAssignment
from app.rules.entities import Rule, RuleAssignment
from app.rules.service import apply_rule
from app.shared.errors import InvariantViolationError, NotFoundError, ValidationError
from app.shared.pagination import Page, PageRequest
from app.shared.ports.database import Database

# --- Requests/responses -------------------------------------------------


@dataclass(frozen=True)
class CreateRuleRequest:
    table_id: int
    factor_values: tuple[tuple[int, int], ...] = ()
    output: str = ""
    title: str | None = None


@dataclass(frozen=True)
class CreateRuleResponse:
    rule: Rule


@dataclass(frozen=True)
class UpdateRuleRequest:
    table_id: int
    rule_id: int
    output: str | None = None
    title: str | None = None
    title_set: bool = False
    factor_values: tuple[tuple[int, int], ...] | None = None
    factor_values_set: bool = False


@dataclass(frozen=True)
class UpdateRuleResponse:
    rule: Rule


@dataclass(frozen=True)
class DeleteRuleRequest:
    table_id: int
    rule_id: int


@dataclass(frozen=True)
class ReorderRulesRequest:
    table_id: int
    ordered_rule_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ReapplyRulesRequest:
    table_id: int


@dataclass(frozen=True)
class ReapplyRulesResponse:
    rules: list[Rule]


@dataclass(frozen=True)
class ListRulesRequest:
    table_id: int
    page: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True)
class ListRulesResponse:
    page: Page[Rule]


@dataclass(frozen=True)
class ListRuleOverlapsRequest:
    table_id: int
    page: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True)
class ListRuleOverlapsResponse:
    page: Page[CombinationOverlap]


class RulesUseCases:
    """The `rules` module's use cases, one method each. Constructed once
    with the app's `Database`."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def create_rule(self, request: CreateRuleRequest) -> CreateRuleResponse:
        """Create a new rule for a decision table and immediately apply it
        to the table's current combinations (spec 005).

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            ValidationError: if `output` is blank, `factor_values` names the
                same factor twice, or names a factor or value not on this
                table.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            if not request.output.strip():
                raise ValidationError("output must not be empty")

            seen: set[int] = set()
            for factor_id, _ in request.factor_values:
                if factor_id in seen:
                    raise ValidationError(
                        f"Factor {factor_id} is assigned more than once in "
                        "the same request"
                    )
                seen.add(factor_id)
            table.validate_factor_value_pairs(list(request.factor_values))

            new_factor_values = [
                RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ]
            existing_rules = await db.rules.list_for_table(request.table_id)

            clean_title = (
                request.title.strip()
                if request.title and request.title.strip()
                else None
            )
            rule = Rule(
                id=None,
                decision_table_id=request.table_id,
                output=request.output,
                title=clean_title,
                order_index=len(
                    existing_rules
                ),  # append at the end (spec 008); drag to reorder afterward
                factor_values=new_factor_values,
            )
            rule = await db.rules.add(rule)

            rule = await apply_rule(db.combinations, db.rules, rule)
            return CreateRuleResponse(rule=rule)

    async def update_rule(self, request: UpdateRuleRequest) -> UpdateRuleResponse:
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
            ValidationError: if `output` is given but blank, `factor_values`
                names the same factor twice, or names a factor or value not
                on this table.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")
            rule = await db.rules.get(request.table_id, request.rule_id)
            if rule is None:
                raise NotFoundError(f"Rule {request.rule_id} not found")

            if request.output is not None:
                if not request.output.strip():
                    raise ValidationError("output must not be empty")
                rule.output = request.output
            if request.title_set:
                rule.title = (
                    request.title.strip()
                    if request.title and request.title.strip()
                    else None
                )

            if request.factor_values_set:
                assert request.factor_values is not None
                seen: set[int] = set()
                for factor_id, _ in request.factor_values:
                    if factor_id in seen:
                        raise ValidationError(
                            f"Factor {factor_id} is assigned more than once "
                            "in the same request"
                        )
                    seen.add(factor_id)
                table.validate_factor_value_pairs(list(request.factor_values))
                rule.factor_values = [
                    RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                    for factor_id, factor_value_id in request.factor_values
                ]

            await db.rules.save(rule)

            if request.factor_values_set or request.output is not None:
                rule = await apply_rule(db.combinations, db.rules, rule)
            return UpdateRuleResponse(rule=rule)

    async def delete_rule(self, request: DeleteRuleRequest) -> None:
        """Delete a rule. Combinations it last patched keep their current
        status/output (see spec 005's "no revert on delete").

        Raises:
            NotFoundError: if `table_id` or `rule_id` doesn't exist.
        """
        async with self._database.transaction() as db:
            # Deleting a rule leaves whatever status/output it last set on
            # combinations untouched — see spec 005's "no revert on delete".
            deleted = await db.rules.delete(request.table_id, request.rule_id)
            if not deleted:
                raise NotFoundError(f"Rule {request.rule_id} not found")

    async def reorder_rules(self, request: ReorderRulesRequest) -> ReapplyRulesResponse:
        """Persists a complete new rule order for a table and immediately
        replays every rule in that order (spec 008) — a reorder is a
        permutation of the table's existing rule ids. Any order is allowed
        (spec 009): a rule that ends up shadowed by a later, more general
        one is the user's call to notice (surfaced via `shadowed_count`/
        `list_rule_overlaps`) and fix by dragging it further down, not
        something the backend rejects.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
            InvariantViolationError: if `ordered_rule_ids` isn't a
                permutation of the table's existing rule ids.
        """
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            existing = await db.rules.list_for_table(request.table_id)
            requested_ids = list(request.ordered_rule_ids)
            if len(requested_ids) != len(set(requested_ids)) or set(requested_ids) != {
                r.id for r in existing
            }:
                raise InvariantViolationError(
                    f"The given rule order must contain every rule of decision "
                    f"table {request.table_id} exactly once"
                )

            by_id = {r.id: r for r in existing}
            for position, rid in enumerate(requested_ids):
                by_id[rid].order_index = position
                await db.rules.save(by_id[rid])

            rules = [
                await apply_rule(db.combinations, db.rules, by_id[rid])
                for rid in requested_ids
            ]
            return ReapplyRulesResponse(rules=rules)

    async def reapply_rules(self, request: ReapplyRulesRequest) -> ReapplyRulesResponse:
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
        async with self._database.transaction() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            rules = await db.rules.list_for_table(request.table_id)
            applied = [
                await apply_rule(db.combinations, db.rules, rule) for rule in rules
            ]
            return ReapplyRulesResponse(rules=applied)

    # --- Reads ------------------------------------------------------------------

    async def list_rules(self, request: ListRulesRequest) -> ListRulesResponse:
        """List a decision table's rules, each tagged with how many of its
        matched combinations are currently shadowed by a later rule (spec 009).

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        async with self._database.snapshot() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            result = await db.rules_reader.list_for_table(
                request.table_id, request.page
            )
            if not result.items:
                return ListRulesResponse(page=result)

            # Shadowing (spec 009) depends on every rule's position/
            # assignment, not just this page's — a rule on this page can be
            # shadowed by one that lives on a different page. Reading both
            # from this one snapshot keeps them consistent with each other.
            all_rules = await db.rules_reader.list_all_for_table(
                request.table_id
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
            shadowed_counts = await db.combinations_reader.count_shadowed_matches(
                request.table_id, rule_inputs
            )
            if not shadowed_counts:
                return ListRulesResponse(page=result)

            items = [
                dataclasses.replace(
                    rule, shadowed_count=shadowed_counts.get(rule.id, 0)
                )
                for rule in result.items
            ]
            return ListRulesResponse(
                page=Page(
                    items=items,
                    total=result.total,
                    limit=result.limit,
                    offset=result.offset,
                )
            )

    async def list_rule_overlaps(
        self, request: ListRuleOverlapsRequest
    ) -> ListRuleOverlapsResponse:
        """See spec 006: rows matched by 2+ of the table's current rules,
        tagged with which rules matched and (last in id order) which one
        currently wins a reapply.

        Raises:
            NotFoundError: if `table_id` doesn't exist.
        """
        async with self._database.snapshot() as db:
            table = await db.tables.get(request.table_id)
            if table is None:
                raise NotFoundError(f"Decision table {request.table_id} not found")

            rules = await db.rules_reader.list_all_for_table(request.table_id)
            rule_inputs = [
                RuleFilterInput(
                    rule_id=rule.id,
                    output=rule.output,
                    title=rule.title,
                    factor_values=tuple(
                        FactorValueAssignment(
                            factor_id=fv.factor_id,
                            factor_value_id=fv.factor_value_id,
                        )
                        for fv in rule.factor_values
                    ),
                )
                for rule in rules
            ]
            page = await db.combinations_reader.list_matched_by_multiple_rules(
                request.table_id, rule_inputs, request.page
            )
            return ListRuleOverlapsResponse(page=page)
