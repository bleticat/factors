"""Read-side port for `Rule` list views.

`Rule` itself (the entity) now carries every field a reader needs
(`created_at`, `shadowed_count` included — see `entities.py`), so there is
no separate read-model type here: `list_for_table`/`list_all_for_table`
return `Rule` entities directly. A single rule by id is loaded the same
way for both reads and writes — `RuleRepository.get` — so this port has no
`get` of its own.
"""

from abc import ABC, abstractmethod

from app.rules.entities import Rule
from app.shared.pagination import Page, PageRequest


class RuleReader(ABC):
    """Read-side port for `Rule` list views."""

    @abstractmethod
    async def list_for_table(self, table_id: int, page: PageRequest) -> Page[Rule]:
        """Return a page of a decision table's rules, ordered by `order_index`."""

    @abstractmethod
    async def list_all_for_table(self, table_id: int) -> list[Rule]:
        """Unpaginated, ordered by `order_index` — the same order rules are
        (re)applied in (spec 008; was creation/id order before it). Used by
        `list_rule_overlaps` (spec 006), which needs every rule's
        assignment to compute overlaps, not one page."""
