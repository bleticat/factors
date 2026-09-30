from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.generation.errors import InvalidGenerationJobTransitionError


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
        return self.status in ACTIVE_STATUSES

    def is_done(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def start(self) -> None:
        if self.status == GenerationJobStatus.PENDING:
            self.status = GenerationJobStatus.RUNNING

    def record_batch(self, new_cursor: int, rows_created: int) -> None:
        if self.status != GenerationJobStatus.RUNNING:
            raise InvalidGenerationJobTransitionError(
                self.id or 0, str(self.status), "batch-progress"
            )
        self.cursor = new_cursor
        self.created_count += rows_created
        if self.cursor >= self.total_combinations:
            self.status = GenerationJobStatus.COMPLETED

    def fail(self, error_message: str) -> None:
        self.status = GenerationJobStatus.FAILED
        self.error_message = error_message

    def cancel(self) -> None:
        if not self.is_active():
            raise InvalidGenerationJobTransitionError(
                self.id or 0, str(self.status), str(GenerationJobStatus.CANCELLED)
            )
        self.status = GenerationJobStatus.CANCELLED
