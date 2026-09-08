"""The boundary that drives a generation job to completion. This loop is not
a use-case method — it opens its own scope per batch, once per iteration,
exactly like a route opens one per request. See the plan's "The async-job
design" section and spec 002 for why this is how the job's incremental,
crash-safe progress is achieved.
"""

from __future__ import annotations

import logging

from app.composition import build_generation_commands, build_rules_commands
from app.generation.entities import TERMINAL_STATUSES, GenerationJobStatus
from app.shared.database.port import Database
from app.shared.execution import run_command

logger = logging.getLogger(__name__)

_TERMINAL_STATUS_VALUES = {str(status) for status in TERMINAL_STATUSES}


async def run_generation_job(database: Database, job_id: int, batch_size: int) -> None:
    while True:
        try:
            result = await run_command(
                database,
                lambda uow: build_generation_commands(uow).generate_combinations_batch(
                    job_id, batch_size
                ),
            )
        except Exception as exc:
            logger.exception("Generation batch failed for job %s", job_id)
            error_message = str(exc)
            try:
                # The failing batch's own transaction already rolled back
                # cleanly; the failure record needs its own fresh commit.
                await run_command(
                    database,
                    lambda uow, error_message=error_message: build_generation_commands(
                        uow
                    ).mark_generation_job_failed(job_id, error_message),
                )
            except Exception:
                logger.exception("Failed to record failure for job %s", job_id)
            return

        if result.status in _TERMINAL_STATUS_VALUES:
            if result.status == str(GenerationJobStatus.COMPLETED):
                # Fresh combinations have no rule-driven output yet — replay
                # this table's rules (spec 005) now that generation is done.
                table_id = result.decision_table_id
                try:
                    await run_command(
                        database,
                        lambda uow, table_id=table_id: build_rules_commands(
                            uow
                        ).reapply_rules(table_id),
                    )
                except Exception:
                    logger.exception("Rule reapply failed for table %s", table_id)
            return
