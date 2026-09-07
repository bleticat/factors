# Generate Combinations

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Once a decision table has factors and values ([001](./001-manage-decision-tables-and-factors.md)), the user triggers generation of the full Cartesian product of factor values as candidate test-case rows (**Combinations**), so they can then review and refine them ([003](./003-review-and-bulk-refine-combinations.md)).

## Behavior

- The projected combination count is `product(len(values) for each factor)`. Generation is rejected outright (no job created, no rows written) if this exceeds `settings.max_combinations` (default 50,000, configurable), or if the table has zero factors, or if any factor has zero values.
- Generation is asynchronous: requesting it creates a `GenerationJob` (`pending`) and returns immediately; the actual row creation happens in the background in batches (default batch size 500, configurable), so progress is visible via polling and the process is not blocked on a single huge transaction.
- A `GenerationJob` has: `status` (`pending` → `running` → one of `completed`/`failed`/`cancelled`), `total_combinations` (known up front from the precheck arithmetic), `created_count` (rows committed so far), `cursor` (position in the mixed-radix combination sequence — the sole source of truth for where the next batch resumes; distinct from `created_count` on purpose, since the two could diverge under skip/retry logic even though they don't in v1), `error_message`.
- Requesting generation on a table that already has combinations deletes and recreates them (delete-and-recreate regeneration semantics in v1 — no incremental merge). The old combinations' review state (status/output) is lost; this is a deliberate v1 scope limitation, not a bug.
- Requesting generation while a job for the same table is already `pending`/`running` is rejected (only one in-flight generation per table).
- Each batch is committed as its own transaction (one `GenerateCombinationsBatchCommand` dispatch = one unit of work), so `created_count`/`cursor` are checkpointed incrementally and a crash mid-run does not lose already-committed batches.
- If a batch fails, the job is marked `failed` with `error_message` set, via a separate command dispatched after the failure (the failing batch's own transaction rolls back cleanly; the failure record itself needs its own committed transaction).
- The user may cancel a `pending`/`running` job; the next batch dispatch observes the `cancelled` status (read fresh at the start of its transaction) and stops without creating further rows.
- On server startup, any job left in `running` status (impossible to legitimately survive a restart, since generation runs in-process) is swept to `failed` with `error_message = "Interrupted by server restart"`.
- While a job is `pending`/`running` for a table, factor/value structure mutations on that table are rejected (see [001](./001-manage-decision-tables-and-factors.md)).

## Commands and Queries

- Command: `RequestGenerationCommand(table_id)` — validates factor/value presence and the combinations cap, creates the `GenerationJob` (`pending`), returns it. The caller (API router) then schedules the background batch loop.
- Command: `GenerateCombinationsBatchCommand(job_id, batch_size)` — reads the job's live `status`/`cursor` inside its own transaction; if not `running`, transitions `pending` → `running` on first call; decomposes the next `batch_size` cursor positions into factor/value picks via mixed-radix arithmetic, bulk-inserts `Combination`+`CombinationValue` rows, advances `cursor`/`created_count`, and marks the job `completed` once `cursor == total_combinations`. Returns `{status, created_count, total_combinations}` so the calling loop knows whether to continue.
- Command: `MarkGenerationJobFailedCommand(job_id, error_message)` — sets `status=failed`.
- Command: `MarkStaleGenerationJobsFailedCommand(job_ids, error_message)` — bulk version, used by the startup sweep.
- Command: `CancelGenerationJobCommand(job_id)` — sets `status=cancelled` from `pending`/`running` only; no-op error if already terminal.
- Query: `GetGenerationJobQuery(job_id)` — current job state, for polling.
- Query: `ListStaleRunningGenerationJobsQuery()` — all jobs with `status == running`, for the startup sweep.

## Test Cases

- Success:
  - Requesting generation for a table with factors [3 values] × [3 values] × [2 values] creates a job with `total_combinations == 18`.
  - Driving `GenerateCombinationsBatchCommand` to completion (batch_size smaller than total, e.g. 5) produces exactly 18 `Combination` rows, each with exactly 3 `CombinationValue` rows (one per factor), and the job ends `completed` with `created_count == 18 == cursor`.
  - Each generated combination's `combination_values` reconstruct a unique tuple across all factors — no duplicate signature within the table, and every possible tuple is represented exactly once.
  - Requesting generation again on the same table deletes the previous 18 combinations and regenerates fresh ones (new `generation_job_id`).
- Validation:
  - `RequestGenerationCommand` on a table with zero factors is rejected, no job created.
  - `RequestGenerationCommand` on a table where some factor has zero values is rejected, no job created.
  - `RequestGenerationCommand` whose projected total exceeds `max_combinations` is rejected with no job and no combinations created (verify with a table configured to exceed a small test-only cap).
  - `RequestGenerationCommand` while a `pending`/`running` job already exists for the table is rejected.
- Edge:
  - `GenerateCombinationsBatchCommand` called again after the job already reached `completed` is a no-op that returns the completed state (does not re-insert or duplicate rows).
  - A batch whose insert violates the unique `(decision_table_id, signature)` constraint (should not happen in normal operation, but guards against a cursor bug) surfaces as a failure recorded via `MarkGenerationJobFailedCommand`, not a silently swallowed error.
  - `CancelGenerationJobCommand` on a `running` job stops the next batch dispatch from creating more rows; job ends `cancelled` with a partial `created_count` preserved (already-committed batches are not rolled back).
  - `CancelGenerationJobCommand` on an already-`completed` job is rejected (no-op error).
- Regression:
  - `ListStaleRunningGenerationJobsQuery` followed by `MarkStaleGenerationJobsFailedCommand` transitions a `running` job to `failed` with the restart message, and does not touch `pending`, `completed`, `failed`, or `cancelled` jobs.
  - Mixed-radix cursor decomposition matches `itertools.product` order exactly for a representative factor/value set (cross-check test against the reference Python iterator for a small case).

## Open Questions

- **Considered and rejected** batching designs (kept here for record, per the plan's mediator-design rationale): (a) a handler issuing multiple `session.commit()` calls inside one command dispatch — breaks the unit-of-work's ownership of commit/rollback (ADR 004); (b) a handler calling the mediator to dispatch its own sub-batches — directly forbidden by the ADR 007 guardrail against handlers calling the mediator; (c) doing all batches inside one single transaction — no incremental progress visibility and risks long SQLite write-lock hold on large tables. The chosen design (external loop, one command per batch) avoids all three.
- None outstanding.
