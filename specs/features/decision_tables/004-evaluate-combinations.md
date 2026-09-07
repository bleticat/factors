# Evaluate Combinations

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Once combinations are reviewed ([003](./003-review-and-bulk-refine-combinations.md)), the table acts as a lookup: given an assignment of some or all factors to specific values, return the matching combination(s) and their status/output — e.g. "what's the expected result when Browser=Chrome, OS=Windows, Login=in?".

## Behavior

- An assignment is a set of `(factor_id, factor_value_id)` pairs, each belonging to the given `table_id`.
- A **full assignment** (exactly one value given for every factor in the table) matches exactly one combination (generation guarantees each tuple is unique per table) — returned as a single result, or a not-found result if the table hasn't been generated (or was regenerated) since the assignment's factors/values were created.
- A **partial assignment** (fewer pairs than the table has factors) matches every combination consistent with the given pairs on the unconstrained factors — returned as a paginated list.
- An assignment containing a `factor_id`/`factor_value_id` pair that doesn't belong to the given `table_id` is rejected as invalid, not silently ignored.
- An empty assignment (`[]`) is treated as a partial assignment matching every combination in the table (paginated) — consistent with [003](./003-review-and-bulk-refine-combinations.md)'s "empty filter means all rows" convention.

## Commands and Queries

- Query: `EvaluateCombinationsQuery(table_id, assignment, page)` — returns either `{kind: "single", result: CombinationDTO | null}` when the assignment is full, or `{kind: "list", page: Page[CombinationDTO]}` when partial/empty. "Full" is determined by comparing the number of distinct factors covered by the assignment against the table's current factor count.

## Test Cases

- Success:
  - Full assignment covering all factors of an 18-combination table returns exactly one matching combination, with whatever status/output was set on it via [003](./003-review-and-bulk-refine-combinations.md).
  - Partial assignment naming one factor's value out of three returns the paginated subset consistent with that one constraint (e.g. 6 of 18 rows for a 3×3×2 table constraining the 2-valued factor).
  - Empty assignment returns all combinations in the table, paginated.
- Validation:
  - An assignment pair whose `factor_id` doesn't belong to `table_id` is rejected.
  - An assignment pair whose `factor_value_id` doesn't belong to the given `factor_id` is rejected.
  - An assignment with two pairs naming the *same* `factor_id` (contradictory/ambiguous) is rejected.
- Edge:
  - Full assignment against a table with no generated combinations (never generated, or generation still in progress) returns `{kind: "single", result: null}`, not an error.
  - Table with a single factor: a full assignment is one pair; verify the "full vs partial" factor-count comparison handles this boundary correctly.

## Open Questions

None.
