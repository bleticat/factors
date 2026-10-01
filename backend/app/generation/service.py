"""Internal helper logic `generation.commands` delegates to. Not part of
the module's public request/response surface."""

from dataclasses import dataclass

from app.generation.entities import GenerationJob


@dataclass(frozen=True)
class GenerationJobRef:
    id: int
    decision_table_id: int
    status: str
    total_combinations: int
    created_count: int
    error_message: str | None = None


def to_ref(job: GenerationJob) -> GenerationJobRef:
    """Project a `GenerationJob` down to the small ref shape use cases return.

    >>> from app.generation.entities import GenerationJobStatus
    >>> job = GenerationJob(
    ...     id=1, decision_table_id=2, status=GenerationJobStatus.RUNNING,
    ...     total_combinations=10, created_count=4,
    ... )
    >>> to_ref(job)
    GenerationJobRef(id=1, decision_table_id=2, status='running', total_combinations=10, created_count=4, error_message=None)
    """
    assert job.id is not None
    return GenerationJobRef(
        id=job.id,
        decision_table_id=job.decision_table_id,
        status=str(job.status),
        total_combinations=job.total_combinations,
        created_count=job.created_count,
        error_message=job.error_message,
    )
