from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationJobDTO:
    id: int
    decision_table_id: int
    status: str
    total_combinations: int
    created_count: int
    error_message: str | None


class GenerationJobReader(ABC):
    """Read-side port for `GenerationJob`."""

    @abstractmethod
    async def get(self, job_id: int) -> GenerationJobDTO | None:
        """Return a job's current status and progress, or None if
        `job_id` doesn't exist."""

    @abstractmethod
    async def list_stale_running(self) -> list[int]:
        """Ids of all jobs currently in `running` status (used by the
        startup sweep — none can legitimately survive a process restart)."""
