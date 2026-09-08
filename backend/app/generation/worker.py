"""The boundary that drives a generation job to completion. This loop is not
a handler — it calls the mediator repeatedly, once per batch, exactly like a
router calls it once. See the plan's "mediator/async-job design" section and
spec 002 for why this is how the job's incremental, crash-safe progress is
achieved without violating ADR 007's "handlers must not call the mediator"
guardrail (that guardrail only constrains code running *inside* a handler).
"""

from __future__ import annotations

import logging

from app.generation.commands import (
    GenerateCombinationsBatchCommand,
    MarkGenerationJobFailedCommand,
)
from app.generation.entities import TERMINAL_STATUSES, GenerationJobStatus
from app.rules.commands import ReapplyRulesCommand
from app.shared.mediator.mediator import Mediator

logger = logging.getLogger(__name__)

_TERMINAL_STATUS_VALUES = {str(status) for status in TERMINAL_STATUSES}


async def run_generation_job(mediator: Mediator, job_id: int, batch_size: int) -> None:
    while True:
        try:
            result = await mediator.execute(
                GenerateCombinationsBatchCommand(job_id=job_id, batch_size=batch_size)
            )
        except Exception as exc:
            logger.exception("Generation batch failed for job %s", job_id)
            try:
                # The failing batch's own transaction already rolled back
                # cleanly; the failure record needs its own fresh commit.
                await mediator.execute(
                    MarkGenerationJobFailedCommand(job_id=job_id, error_message=str(exc))
                )
            except Exception:
                logger.exception("Failed to record failure for job %s", job_id)
            return

        if result.status in _TERMINAL_STATUS_VALUES:
            if result.status == str(GenerationJobStatus.COMPLETED):
                # Fresh combinations have no rule-driven output yet — replay
                # this table's rules (spec 005) now that generation is done.
                try:
                    await mediator.execute(ReapplyRulesCommand(table_id=result.decision_table_id))
                except Exception:
                    logger.exception("Rule reapply failed for table %s", result.decision_table_id)
            return
