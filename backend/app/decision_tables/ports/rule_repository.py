from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.decision_tables.domain.rule import Rule


class RuleRepository(ABC):
    """Write-side port for `Rule`. `list_for_table` returns id order — the
    same order rules are (re)applied in (see spec 005's "later rule wins"
    replay rule)."""

    @abstractmethod
    async def add(self, rule: Rule) -> Rule: ...

    @abstractmethod
    async def get(self, table_id: int, rule_id: int) -> Rule | None: ...

    @abstractmethod
    async def list_for_table(self, table_id: int) -> list[Rule]: ...

    @abstractmethod
    async def delete(self, table_id: int, rule_id: int) -> bool:
        """Returns whether a matching rule was found and deleted."""

    @abstractmethod
    async def delete_all_for_table(self, table_id: int) -> None:
        """Used when a factor/factor value is deleted — see spec 005's
        whole-set rule invalidation, mirroring `Combination.
        delete_all_for_table`."""

    @abstractmethod
    async def record_apply(self, rule_id: int, matched_count: int, applied_at: datetime) -> None:
        """Persist the outcome of (re)applying a rule."""
