# Manage Decision Tables and Factors

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

A user creates a **Decision Table** to hold a combinatorial test-case matrix, then defines the **Factors** (variables) and their possible **Factor Values** that the table will later be generated from. This is the setup phase that precedes combination generation (see [002](./002-generate-combinations.md)).

## Behavior

- A decision table has a `name` (required, non-empty) and an optional `description`.
- A factor belongs to exactly one decision table, has a `name` unique within that table, and an `order_index` that determines its position in generated combination tuples and in the UI. New factors are appended at the end.
- A factor value belongs to exactly one factor, has a `value` (text) unique within that factor, and an `order_index`. New values are appended at the end.
- Renaming/reordering a factor or value, or deleting one, is allowed at any time **except** while the owning decision table has a `GenerationJob` in status `pending` or `running` — generation reads factor/value ordering to decompose its cursor (mixed-radix arithmetic, see [002](./002-generate-combinations.md)), so structure must stay stable mid-run. Such attempts are rejected with a domain error (`GenerationInProgressError`), not silently queued.
- Deleting a factor or a factor value invalidates any combinations already generated for the table (their `signature` no longer corresponds to the current structure), so it also deletes all existing `Combination`/`CombinationValue` rows for that table. This is a destructive, immediate cascade in v1 (no confirmation workflow beyond what the frontend chooses to add) — there is no versioning/undo in scope.
- Deleting a decision table cascades to its factors, factor values, combinations, and generation jobs.
- Listing decision tables returns lightweight summaries (id, name, description, factor count) ordered by most recently created first. Getting a single table returns it with its factors and each factor's values, ordered by `order_index`.

## Commands and Queries

- Command: `CreateDecisionTableCommand(name, description)` — creates and returns the table.
- Command: `UpdateDecisionTableCommand(table_id, name, description)` — renames/redescribes.
- Command: `DeleteDecisionTableCommand(table_id)` — deletes, cascading.
- Command: `AddFactorCommand(table_id, name)` — appends a factor. Rejected if a generation job is pending/running, or if the name is a duplicate within the table.
- Command: `UpdateFactorCommand(table_id, factor_id, name, order_index)` — renames/reorders. Same lock rule.
- Command: `DeleteFactorCommand(table_id, factor_id)` — deletes a factor and cascades combination deletion. Same lock rule.
- Command: `AddFactorValueCommand(table_id, factor_id, value)` — appends a value. Same lock rule; duplicate value within the factor is rejected.
- Command: `UpdateFactorValueCommand(table_id, factor_id, value_id, value, order_index)` — renames/reorders. Same lock rule.
- Command: `DeleteFactorValueCommand(table_id, factor_id, value_id)` — deletes a value and cascades combination deletion. Same lock rule.
- Query: `GetDecisionTableQuery(table_id)` — table with nested factors and values.
- Query: `ListDecisionTablesQuery(page)` — paginated summaries.

All commands/queries owned by `decision_tables`.

## Test Cases

- Success:
  - Create a table with a name and description; it is retrievable via `GetDecisionTableQuery` with an empty factor list.
  - Add a factor to a table; it appears in `GetDecisionTableQuery` with `order_index == 0` and an empty value list.
  - Add a second factor; it gets `order_index == 1` and the first factor is unaffected.
  - Add a value to a factor; it appears with `order_index == 0`.
  - Update a factor's name; `GetDecisionTableQuery` reflects the new name, `order_index` unchanged unless explicitly changed.
  - Delete a factor value that is not the last one; remaining values keep their existing `order_index` (no automatic renumbering required in v1 — order is by `order_index`, gaps are fine).
  - `ListDecisionTablesQuery` returns multiple tables ordered most-recently-created first, with correct factor counts.
  - Delete a decision table; a subsequent `GetDecisionTableQuery` raises `DecisionTableNotFoundError`.
- Validation:
  - `CreateDecisionTableCommand` with an empty name is rejected.
  - `AddFactorCommand` with a name already used by another factor in the same table is rejected with `DuplicateFactorNameError`; the same name in a *different* table succeeds.
  - `AddFactorValueCommand` with a value already used by another value in the same factor is rejected with `DuplicateFactorValueError`.
  - Any factor/value mutation command against a table with a `pending` or `running` `GenerationJob` is rejected with `GenerationInProgressError`; the same command succeeds once the job reaches `completed`, `failed`, or `cancelled`.
- Edge:
  - `AddFactorCommand`/`AddFactorValueCommand`/`GetDecisionTableQuery`/etc. against a non-existent `table_id` raise `DecisionTableNotFoundError`.
  - `UpdateFactorCommand`/`DeleteFactorCommand` against a `factor_id` that exists but belongs to a different table raise `FactorNotFoundError`.
  - Deleting a factor that already has generated combinations removes those combinations (and their `combination_values`) along with it.
- Regression:
  - Deleting one factor value does not delete or renumber sibling values of other factors.

## Open Questions

None.
