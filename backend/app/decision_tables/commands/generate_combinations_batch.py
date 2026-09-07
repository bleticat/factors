"""The batching command at the heart of the generation design (see the
plan's "The mediator/async-job design" section and spec 002). One dispatch
of this command = one unit of work = one transaction = one commit. The
background loop (`decision_tables/background/generation_worker.py`) calls
this repeatedly; it is itself a boundary, not a handler, so it may call the
mediator in a loop without violating ADR 007's "handlers must not call the
mediator" guardrail.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands._job_refs import to_ref
from app.decision_tables.commands.results import GenerationJobRef
from app.decision_tables.domain.combination import (
    Combination,
    CombinationValue,
    build_signature,
    decompose_index,
)
from app.decision_tables.domain.errors import (
    DecisionTableNotFoundError,
    GenerationJobNotFoundError,
)
from app.decision_tables.domain.generation_job import TERMINAL_STATUSES
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.decision_tables.ports.decision_table_repository import DecisionTableRepository
from app.decision_tables.ports.generation_job_repository import GenerationJobRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class GenerateCombinationsBatchCommand(Command[GenerationJobRef]):
    job_id: int
    batch_size: int = 500


class GenerateCombinationsBatchHandler:
    def __init__(
        self,
        jobs: GenerationJobRepository,
        tables: DecisionTableRepository,
        combinations: CombinationRepository,
    ) -> None:
        self._jobs = jobs
        self._tables = tables
        self._combinations = combinations

    async def handle(self, request: GenerateCombinationsBatchCommand) -> GenerationJobRef:
        # Read live status/cursor fresh, inside this dispatch's own
        # transaction — the job row is the sole source of truth, so this
        # handler (and the loop driving it) carries no state of its own
        # and can safely resume after a crash or observe a concurrent
        # cancel (see spec 002).
        job = await self._jobs.get_for_update(request.job_id)
        if job is None:
            raise GenerationJobNotFoundError(request.job_id)

        if job.status in TERMINAL_STATUSES:
            # Idempotent no-op: already completed/failed/cancelled.
            return to_ref(job)

        job.start()

        table = await self._tables.get(job.decision_table_id)
        if table is None:
            raise DecisionTableNotFoundError(job.decision_table_id)

        ordered_factors = table.ordered_factors()
        value_counts = [len(f.values) for f in ordered_factors]

        batch_end = min(job.cursor + request.batch_size, job.total_combinations)
        new_combinations = [
            self._build_combination(job.decision_table_id, job.id or 0, ordered_factors, value_counts, index)
            for index in range(job.cursor, batch_end)
        ]

        await self._combinations.bulk_insert(new_combinations)
        job.record_batch(new_cursor=batch_end, rows_created=len(new_combinations))
        await self._jobs.save(job)

        return to_ref(job)

    @staticmethod
    def _build_combination(table_id: int, job_id: int, ordered_factors, value_counts, index: int) -> Combination:
        picks = decompose_index(index, value_counts)
        factor_value_ids = [
            ordered_factors[i].values[picks[i]].id or 0 for i in range(len(ordered_factors))
        ]
        return Combination(
            id=None,
            decision_table_id=table_id,
            generation_job_id=job_id,
            signature=build_signature(factor_value_ids),
            values=[
                CombinationValue(factor_id=ordered_factors[i].id or 0, factor_value_id=factor_value_ids[i])
                for i in range(len(ordered_factors))
            ],
        )
