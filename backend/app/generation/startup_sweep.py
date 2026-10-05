from app.generation.use_cases import (
    GenerationUseCases,
    MarkStaleGenerationJobsFailedRequest,
)
from app.shared.ports.database import Database

INTERRUPTED_MESSAGE = "Interrupted by server restart"


async def sweep_stale_generation_jobs(database: Database) -> int:
    use_cases = GenerationUseCases(database)
    stale = await use_cases.list_stale_running_generation_jobs()
    if not stale.job_ids:
        return 0
    response = await use_cases.mark_stale_generation_jobs_failed(
        MarkStaleGenerationJobsFailedRequest(stale.job_ids, INTERRUPTED_MESSAGE)
    )
    return response.updated_count
