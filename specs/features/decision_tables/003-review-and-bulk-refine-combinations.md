# Review and Bulk-Refine Combinations

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

After generation ([002](./002-generate-combinations.md)) produces candidate combinations, the user reviews them and marks each as a usable test case (`possible`, with an expected-result `output`) or excludes it (`impossible`, with an optional reason). Reviewing thousands of rows one at a time is impractical, so bulk edits over a filtered set are required alongside per-row edits.

## Behavior

- Each combination has `status` (`unreviewed` default, `possible`, or `impossible`), `output` (free text, meaningful when `possible`), and `impossible_reason` (free text, meaningful when `impossible`). Setting `output`/`impossible_reason` is not restricted to the "matching" status — the API stores whatever is sent; the frontend is responsible for the UX of clearing the irrelevant field when status changes, but the backend does not silently null it out.
- Listing combinations supports filtering by `status` and by an AND-ed set of `(factor_id, factor_value_id)` constraints (e.g. "all rows where Browser = Safari and OS = Mac"), plus pagination. This is the same filter shape used by bulk-patch, so "filter to see, then bulk-apply to the filtered set" is one consistent mental model.
- A single combination can be patched by id (`status`, `output`, `impossible_reason`, each optional/independently updatable).
- A bulk patch takes the same filter shape as listing plus a patch payload, and applies the patch to every matching row within the table in one set-based database operation (not loaded entity-by-entity). It returns the count of matched/updated rows so the caller can confirm the scope of the change before or after applying it.
- Both single and bulk patches operate only on combinations belonging to the given `table_id`; a `combination_id` that exists but belongs to another table is treated as not found.

## Commands and Queries

- Command: `PatchCombinationCommand(table_id, combination_id, status, output, impossible_reason)` — status/output/impossible_reason each optional (unset fields left unchanged).
- Command: `BulkPatchCombinationsCommand(table_id, filter, patch)` — `filter: {status?, factor_values?: [(factor_id, factor_value_id), ...]}`, `patch: {status?, output?, impossible_reason?}`. Returns `{matched_count, updated_count}`.
- Query: `ListCombinationsQuery(table_id, filter, page)` — same filter shape as the bulk command; returns a page of combination DTOs (each including its resolved factor/value assignment).

## Test Cases

- Success:
  - Patch a single combination's status to `possible` with an output string; `ListCombinationsQuery` reflects it.
  - Patch a single combination's status to `impossible` with a reason; reflected the same way.
  - Bulk-patch filtered by `status=unreviewed` and one `(factor_id, factor_value_id)` constraint sets status/reason on exactly the matching subset; non-matching rows (different factor value, or already non-`unreviewed`) are untouched.
  - Bulk-patch filtered by two AND-ed `(factor_id, factor_value_id)` constraints (different factors) matches only rows satisfying both.
  - `ListCombinationsQuery` filtered by `status=possible` returns only previously-marked-possible rows, paginated correctly across a page boundary.
- Validation:
  - `PatchCombinationCommand`/`BulkPatchCombinationsCommand` with a `status` value outside `{unreviewed, possible, impossible}` is rejected.
  - A `factor_id`/`factor_value_id` pair in a filter that doesn't belong to the given `table_id` is rejected (400-equivalent domain error), not silently ignored.
- Edge:
  - `PatchCombinationCommand` for a `combination_id` belonging to a different table raises `CombinationNotFoundError`.
  - Bulk-patch whose filter matches zero rows returns `{matched_count: 0, updated_count: 0}` without error.
  - Bulk-patch with an empty filter (`{}`) matches and patches every combination in the table — verify this is intentional/expected, not an accidental no-op or an accidental full-table wipe surprise (documented behavior: empty filter means "all rows in this table").
- Regression:
  - Bulk-patching one table's combinations never touches another table's combinations, even if both tables happen to share identical factor/value id ranges is not possible (ids are global), but verify cross-table isolation via the `table_id` scoping regardless.

## Open Questions

None.
