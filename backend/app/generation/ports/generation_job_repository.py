from abc import ABC, abstractmethod

from app.generation.entities import GenerationJob


class GenerationJobRepository(ABC):
    """Write-side port for the `GenerationJob` entity (single row, load-
    mutate-save whole)."""

    @abstractmethod
    async def add(self, job: GenerationJob) -> GenerationJob:
        """Insert a new job and populate its generated `id` in place."""

    @abstractmethod
    async def get(self, job_id: int) -> GenerationJob | None:
        """Return a job, or None if `job_id` doesn't exist."""

    @abstractmethod
    async def get_for_update(self, job_id: int) -> GenerationJob | None:
        """Like `get`, but the caller intends to mutate and `save` within
        the same transaction — read fresh, not from any cache."""

    @abstractmethod
    async def save(self, job: GenerationJob) -> None:
        """Persist a job's current status/progress fields."""

    @abstractmethod
    async def has_active_job(self, table_id: int) -> bool:
        """True if `table_id` has a job in `pending` or `running` status."""

    @abstractmethod
    async def mark_failed_bulk(self, job_ids: list[int], error_message: str) -> int:
        """Set-based transition of `running` jobs to `failed`. Returns the
        number of rows updated."""
