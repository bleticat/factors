from __future__ import annotations

from app.decision_tables.commands.results import GenerationJobRef
from app.decision_tables.domain.generation_job import GenerationJob


def to_ref(job: GenerationJob) -> GenerationJobRef:
    assert job.id is not None
    return GenerationJobRef(
        id=job.id,
        decision_table_id=job.decision_table_id,
        status=str(job.status),
        total_combinations=job.total_combinations,
        created_count=job.created_count,
        error_message=job.error_message,
    )
