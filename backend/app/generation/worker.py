"""The boundary that drives a generation job to completion. This loop is not
a use-case method — it constructs `GenerationUseCases(database)`/
`RulesUseCases(database)` fresh per step, exactly like a route builds its
own use cases per request. See the plan's "The async-job design" section
and spec 002 for why this is how the job's incremental, crash-safe
progress is achieved.
"""

import logging

from app.generation.entities import TERMINAL_STATUSES, GenerationJobStatus
from app.generation.use_cases import GenerationUseCases
from app.rules.use_cases import RulesUseCases
from app.shared.ports.database import Database

logger = logging.getLogger(__name__)

_TERMINAL_STATUS_VALUES = {str(status) for status in TERMINAL_STATUSES}


async def run_generation_job(database: Database, job_id: int, batch_size: int) -> None:
    """Drive a generation job to completion (or failure), one
    `batch_size`-row batch and one transaction at a time, then reapply the
    table's rules once generation completes. Marks the job failed and
    returns if a batch raises."""
    generation = GenerationUseCases(database)
    while True:
        try:
            result = await generation.generate_combinations_batch(job_id, batch_size)
        except Exception as exc:
            logger.exception("Generation batch failed for job %s", job_id)
            try:
                # The failing batch's own transaction already rolled back
                # cleanly; the failure record needs its own fresh commit.
                await generation.mark_generation_job_failed(job_id, str(exc))
            except Exception:
                logger.exception("Failed to record failure for job %s", job_id)
            return

        if result.status in _TERMINAL_STATUS_VALUES:
            if result.status == str(GenerationJobStatus.COMPLETED):
                # Fresh combinations have no rule-driven output yet — replay
                # this table's rules (spec 005) now that generation is done.
                table_id = result.decision_table_id
                try:
                    await RulesUseCases(database).reapply_rules(table_id)
                except Exception:
                    logger.exception("Rule reapply failed for table %s", table_id)
            return
