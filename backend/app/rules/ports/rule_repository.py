from abc import ABC, abstractmethod
from datetime import datetime

from app.rules.entities import Rule


class RuleRepository(ABC):
    """Write-side port for `Rule`. `list_for_table` returns `order_index`
    order — the same order rules are (re)applied in (see spec 005's "later
    rule wins" replay rule and spec 008's explicit, editable ordering)."""

    @abstractmethod
    async def add(self, rule: Rule) -> Rule:
        """Insert a new rule and populate its generated `id` in place."""

    @abstractmethod
    async def get(self, table_id: int, rule_id: int) -> Rule | None:
        """Return one rule, or None if it doesn't exist on this table."""

    @abstractmethod
    async def list_for_table(self, table_id: int) -> list[Rule]:
        """Return every rule for a table, ordered by `order_index`."""

    @abstractmethod
    async def save(self, rule: Rule) -> None:
        """Persist `output`/`title`/`order_index`/`factor_values` for an
        already-existing rule (spec 008) — a full replace of its assignment,
        not a diff, since the whole `factor_values` list is always supplied
        by the caller."""

    @abstractmethod
    async def delete(self, table_id: int, rule_id: int) -> bool:
        """Returns whether a matching rule was found and deleted."""

    @abstractmethod
    async def delete_all_for_table(self, table_id: int) -> None:
        """Used when a factor/factor value is deleted — see spec 005's
        whole-set rule invalidation, mirroring `Combination.
        delete_all_for_table`."""

    @abstractmethod
    async def record_apply(
        self, rule_id: int, matched_count: int, applied_at: datetime
    ) -> None:
        """Persist the outcome of (re)applying a rule."""
