from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.generation.errors import InvalidGenerationJobTransitionError


class GenerationJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = (GenerationJobStatus.PENDING, GenerationJobStatus.RUNNING)
TERMINAL_STATUSES = (
    GenerationJobStatus.COMPLETED,
    GenerationJobStatus.FAILED,
    GenerationJobStatus.CANCELLED,
)


@dataclass
class GenerationJob:
    id: int | None
    decision_table_id: int
    status: GenerationJobStatus
    total_combinations: int
    created_count: int = 0
    cursor: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def is_active(self) -> bool:
        """Return whether this job is still pending or running."""
        return self.status in ACTIVE_STATUSES

    def is_done(self) -> bool:
        """Return whether this job has reached a terminal status."""
        return self.status in TERMINAL_STATUSES

    def start(self) -> None:
        """Transition a pending job to running. A no-op if already running."""
        if self.status == GenerationJobStatus.PENDING:
            self.status = GenerationJobStatus.RUNNING

    def record_batch(self, new_cursor: int, rows_created: int) -> None:
        """Advance the job's cursor/created_count after a batch is inserted,
        completing the job once the cursor reaches `total_combinations`.

        Raises:
            InvalidGenerationJobTransitionError: if the job isn't `running`.
        """
        if self.status != GenerationJobStatus.RUNNING:
            raise InvalidGenerationJobTransitionError(
                self.id or 0, str(self.status), "batch-progress"
            )
        self.cursor = new_cursor
        self.created_count += rows_created
        if self.cursor >= self.total_combinations:
            self.status = GenerationJobStatus.COMPLETED

    def fail(self, error_message: str) -> None:
        """Mark the job failed with `error_message`."""
        self.status = GenerationJobStatus.FAILED
        self.error_message = error_message

    def cancel(self) -> None:
        """Cancel the job.

        Raises:
            InvalidGenerationJobTransitionError: if the job isn't active
                (already terminal).
        """
        if not self.is_active():
            raise InvalidGenerationJobTransitionError(
                self.id or 0, str(self.status), str(GenerationJobStatus.CANCELLED)
            )
        self.status = GenerationJobStatus.CANCELLED
