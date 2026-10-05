"""Read-side port for `GenerationJob` list views.

A single job by id is loaded the same way for both reads and writes —
`GenerationJobRepository.get` — so this port has no `get` of its own; it
only exists for `list_stale_running`, a query shape (just ids, no full
entity) a plain load-by-id can't give.
"""

from abc import ABC, abstractmethod


class GenerationJobReader(ABC):
    """Read-side port for `GenerationJob` list views."""

    @abstractmethod
    async def list_stale_running(self) -> list[int]:
        """Ids of all jobs currently in `running` status (used by the
        startup sweep — none can legitimately survive a process restart)."""
