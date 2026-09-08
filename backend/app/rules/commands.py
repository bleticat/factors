"""Write-side use cases for the `rules` module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.combinations.ports.combination_repository import CombinationRepository
from app.rules.entities import Rule, RuleAssignment
from app.rules.errors import InvalidRuleOrderError, RuleNotFoundError
from app.rules.ports.rule_repository import RuleRepository
from app.rules.service import RuleApplyRef, apply_rule
from app.shared.errors import DuplicateFactorInAssignmentError, EmptyNameError
from app.shared.mediator.requests import Command
from app.tables.errors import DecisionTableNotFoundError
from app.tables.ports.decision_table_repository import DecisionTableRepository


@dataclass(frozen=True)
class RuleRef:
    id: int
    matched_count: int
    applied_at: datetime | None


@dataclass(frozen=True)
class ReapplyRulesResult:
    results: list[RuleApplyRef]


@dataclass(frozen=True)
class CreateRuleCommand(Command[RuleRef]):
    table_id: int
    factor_values: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    output: str = ""
    title: str | None = None


class CreateRuleHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: CreateRuleCommand) -> RuleRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        if not request.output.strip():
            raise EmptyNameError("output")

        seen: set[int] = set()
        for factor_id, _ in request.factor_values:
            if factor_id in seen:
                raise DuplicateFactorInAssignmentError(factor_id)
            seen.add(factor_id)
        table.validate_factor_value_pairs(list(request.factor_values))

        new_factor_values = [
            RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
            for factor_id, factor_value_id in request.factor_values
        ]
        existing_rules = await self._rules.list_for_table(request.table_id)

        title = request.title.strip() if request.title and request.title.strip() else None
        rule = Rule(
            id=None,
            decision_table_id=request.table_id,
            output=request.output,
            title=title,
            order_index=len(existing_rules),  # append at the end (spec 008); drag to reorder afterward
            factor_values=new_factor_values,
        )
        rule = await self._rules.add(rule)

        applied = await apply_rule(self._combinations, self._rules, rule)
        return RuleRef(id=applied.rule_id, matched_count=applied.matched_count, applied_at=applied.applied_at)


@dataclass(frozen=True)
class UpdateRuleCommand(Command[RuleRef]):
    """Edits an existing rule's output/title/assignment in place, without
    changing its position (`order_index`) — see spec 008/009. Reordering is
    a separate command (`ReorderRulesCommand`), done from the "Saved rules"
    list; any assignment is allowed regardless of how general it is relative
    to other rules (spec 009) — a rule shadowed by a later, more general one
    is the user's call to notice and fix (surfaced via
    `ListRuleOverlapsQuery`/`ListRulesQuery`'s `shadowed_count`), not
    something the backend blocks."""

    table_id: int
    rule_id: int
    output: str | None = None
    title: str | None = None
    title_set: bool = False
    factor_values: tuple[tuple[int, int], ...] | None = None
    factor_values_set: bool = False


class UpdateRuleHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: UpdateRuleCommand) -> RuleRef:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)
        rule = await self._rules.get(request.table_id, request.rule_id)
        if rule is None:
            raise RuleNotFoundError(request.rule_id)

        if request.output is not None:
            if not request.output.strip():
                raise EmptyNameError("output")
            rule.output = request.output
        if request.title_set:
            rule.title = request.title.strip() if request.title and request.title.strip() else None

        if request.factor_values_set:
            assert request.factor_values is not None
            seen: set[int] = set()
            for factor_id, _ in request.factor_values:
                if factor_id in seen:
                    raise DuplicateFactorInAssignmentError(factor_id)
                seen.add(factor_id)
            table.validate_factor_value_pairs(list(request.factor_values))
            rule.factor_values = [
                RuleAssignment(factor_id=factor_id, factor_value_id=factor_value_id)
                for factor_id, factor_value_id in request.factor_values
            ]

        await self._rules.save(rule)

        if request.factor_values_set or request.output is not None:
            applied = await apply_rule(self._combinations, self._rules, rule)
            return RuleRef(id=applied.rule_id, matched_count=applied.matched_count, applied_at=applied.applied_at)
        return RuleRef(id=rule.id, matched_count=rule.matched_count, applied_at=rule.applied_at)


@dataclass(frozen=True)
class DeleteRuleCommand(Command[None]):
    table_id: int
    rule_id: int


class DeleteRuleHandler:
    def __init__(self, rules: RuleRepository) -> None:
        self._rules = rules

    async def handle(self, request: DeleteRuleCommand) -> None:
        # Deleting a rule leaves whatever status/output it last set on
        # combinations untouched — see spec 005's "no revert on delete".
        deleted = await self._rules.delete(request.table_id, request.rule_id)
        if not deleted:
            raise RuleNotFoundError(request.rule_id)


@dataclass(frozen=True)
class ReorderRulesCommand(Command[ReapplyRulesResult]):
    """Persists a complete new rule order for a table and immediately
    replays every rule in that order (spec 008) — a reorder is a permutation
    of the table's existing rule ids. Any order is allowed (spec 009): a
    rule that ends up shadowed by a later, more general one is the user's
    call to notice (surfaced via `shadowed_count`/`ListRuleOverlapsQuery`)
    and fix by dragging it further down, not something the backend
    rejects."""

    table_id: int
    ordered_rule_ids: tuple[int, ...] = field(default_factory=tuple)


class ReorderRulesHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ReorderRulesCommand) -> ReapplyRulesResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        existing = await self._rules.list_for_table(request.table_id)
        requested_ids = list(request.ordered_rule_ids)
        if len(requested_ids) != len(set(requested_ids)) or set(requested_ids) != {r.id for r in existing}:
            raise InvalidRuleOrderError(request.table_id)

        by_id = {r.id: r for r in existing}
        for position, rid in enumerate(requested_ids):
            by_id[rid].order_index = position
            await self._rules.save(by_id[rid])

        results = [await apply_rule(self._combinations, self._rules, by_id[rid]) for rid in requested_ids]
        return ReapplyRulesResult(results=results)


@dataclass(frozen=True)
class ReapplyRulesCommand(Command[ReapplyRulesResult]):
    """Replays every rule for a table against its current combinations, in
    creation order, so a later rule's output wins on any row both it and an
    earlier rule match (see spec 005). Invoked automatically by the
    generation worker once a job reaches `completed`, and exposed for
    on-demand use. Bounded by the table's rule count (not by combination
    count), so — unlike generation — it fits in a single command/transaction
    without batching."""

    table_id: int


class ReapplyRulesHandler:
    def __init__(
        self,
        tables: DecisionTableRepository,
        rules: RuleRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._tables = tables
        self._rules = rules
        self._combinations = combinations

    async def handle(self, request: ReapplyRulesCommand) -> ReapplyRulesResult:
        table = await self._tables.get(request.table_id)
        if table is None:
            raise DecisionTableNotFoundError(request.table_id)

        rules = await self._rules.list_for_table(request.table_id)
        results = [await apply_rule(self._combinations, self._rules, rule) for rule in rules]
        return ReapplyRulesResult(results=results)
