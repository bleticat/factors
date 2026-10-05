import dataclasses
from dataclasses import dataclass, field

from factors.features.combinations.ports.combination_reader import (
    CombinationOverlap,
    RuleFilterInput,
)
from factors.features.combinations.ports.combination_repository import (
    FactorValueAssignment,
)
from factors.features.rules.entities import Rule, RuleAssignment
from factors.features.rules.service import apply_rule
from factors.shared.errors import (
    InvariantViolationError,
    NotFoundError,
    ValidationError,
)
from factors.shared.pagination import Page, PageRequest
from factors.shared.ports.database import Database

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
    def __init__(self, database: Database) -> None:
        self._database = database

    # --- Writes ---------------------------------------------------------------

    async def create_rule(self, request: CreateRuleRequest) -> CreateRuleResponse:
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
        async with self._database.transaction() as db:
            # Deleting a rule leaves whatever status/output it last set on
            # combinations untouched — see spec 005's "no revert on delete".
            deleted = await db.rules.delete(request.table_id, request.rule_id)
            if not deleted:
                raise NotFoundError(f"Rule {request.rule_id} not found")

    async def reorder_rules(self, request: ReorderRulesRequest) -> ReapplyRulesResponse:
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
