from app.generation.ports.generation_job_repository import GenerationJobRepository
from app.shared.errors import InvariantViolationError


async def ensure_not_generating(jobs: GenerationJobRepository, table_id: int) -> None:
    if await jobs.has_active_job(table_id):
        raise InvariantViolationError(
            f"Decision table {table_id} has a generation job in progress; "
            "structure cannot change until it finishes"
        )
