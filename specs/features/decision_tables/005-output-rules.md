# Output Rules

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Reviewing combinations one filtered batch at a time ([003](./003-review-and-bulk-refine-combinations.md)) works, but the user often already knows the answer as a general rule before looking at any row: "whenever Browser=Safari, the output is always 'Not supported', no matter the OS or Login state." Today that's a one-off bulk-patch — apply once, forget it happened. This feature makes that statement a saved **rule**: a partial factor→value assignment (unset factors implicitly mean "any value") plus an output, kept as its own record so it can be reviewed, listed, and — critically — re-applied automatically when the table is regenerated (new factor values mean new rows the rule should also cover).

## Behavior

- A **rule** belongs to one `decision_table_id` and has:
  - an **assignment**: zero or more `(factor_id, factor_value_id)` pairs, each naming a distinct factor belonging to the table (same shape/validation as the bulk-patch filter in [003](./003-review-and-bulk-refine-combinations.md) and the evaluate assignment in [004](./004-evaluate-combinations.md)). Factors left unassigned act as a wildcard — "any value of this factor" — exactly like the existing filter UI's "any" option.
  - an **output**: required, non-empty free text.
  - An empty assignment (`[]`) is a valid rule — it matches every combination in the table (a table-wide default output), consistent with [003](./003-review-and-bulk-refine-combinations.md)'s "empty filter means all rows" convention.
- Creating a rule immediately applies it: every existing combination matching the assignment is set to `status=possible`, `output=<the rule's output>` — the same set-based update `BulkPatchCombinationsCommand` performs, using the rule's assignment as the filter. The number of rows matched by that apply is recorded on the rule (`matched_count`, `applied_at`) and returned to the caller so the UI can show "this rule affects N rows" right after saving.
- Rules are re-applied automatically whenever a generation job for their table finishes successfully (i.e. after [002](./002-generate-combinations.md)'s delete-and-recreate regeneration produces a fresh set of combinations, which have no rule-driven output yet). All of a table's rules are replayed in creation order; where two rules' assignments both match the same row, the **later-created rule wins** (last write in creation order), because replay is just a sequence of the same set-based update rule creation itself performs. Each rule's `matched_count`/`applied_at` is refreshed by the replay. Rules can also be replayed on demand (without waiting for a regeneration) via the same reapply operation. [007](./007-reject-more-general-rules.md) constrains which rules can coexist in the first place: a new rule is rejected outright if it is as general as or more general than an already-existing rule, so in practice "later wins" only ever resolves in favor of a *refinement* of the rules created before it, never a silent regression to something broader.
- Deleting a rule removes only the rule record. It does **not** revert the `status`/`output` it previously set on combinations — those rows keep whatever they were last set to (by this rule, a later rule, or a manual edit). Tracking per-row rule provenance to support "revert on delete" is out of scope for this MVP (see Open Questions).
- A rule whose assignment references a `factor_id`/`factor_value_id` that doesn't belong to the table is rejected, not silently ignored — same as the bulk-patch filter and evaluate assignment.
- An assignment with two pairs naming the same `factor_id` is rejected as contradictory/ambiguous — same as evaluate ([004](./004-evaluate-combinations.md)).
- Deleting a factor or a factor value invalidates that table's existing combinations ([001](./001-manage-decision-tables-and-factors.md)'s cascade). Since a rule's assignment can reference the deleted factor/value, and rules are only meaningful against the table's current structure, deleting a factor or factor value also deletes **all** of that table's rules (not just the ones referencing the deleted factor/value) — the same blunt, whole-set invalidation already applied to combinations, rather than a partial-assignment rewrite that would silently change a rule's meaning.
- Listing rules for a table is paginated, ordered by creation (the same order they're replayed in), and does not require combinations to exist yet — a rule can be authored before the table has ever been generated; it simply matches zero rows until generation happens (and its `matched_count` will be 0 until then).

## Commands and Queries

- Command: `CreateRuleCommand(table_id, factor_values, output)` — validates the assignment (pairs belong to the table, no duplicate factor), rejects empty `output`, persists the rule, applies it immediately, and returns `RuleRef(id, matched_count, applied_at)`.
- Command: `DeleteRuleCommand(table_id, rule_id)` — deletes the rule; raises `RuleNotFoundError` if it doesn't belong to `table_id`.
- Command: `ReapplyRulesCommand(table_id)` — replays every rule for the table, in creation order, against the table's current combinations; returns the per-rule results. Invoked automatically by the generation worker after a job reaches `completed`, and exposed for on-demand use.
- Query: `ListRulesQuery(table_id, page)` — returns a paginated `RuleDTO` list (assignment, output, `matched_count`, `applied_at`, `created_at`), ordered by id.

## Test Cases

- Success:
  - Creating a rule with a single-factor assignment on the 18-combination standard table (3×3×2) immediately sets `status=possible`/`output` on exactly the matching subset and returns that count as `matched_count`.
  - Creating a rule with an empty assignment (`[]`) matches and updates all 18 rows.
  - `ListRulesQuery` reflects a created rule's assignment, output, and `matched_count`.
  - After regenerating a table (new factor value added, then `RequestGenerationCommand` re-run to completion), previously-created rules are automatically re-applied to the fresh combination set, including rows covering the new factor value.
  - Two overlapping rules (a broad one, then a narrower one created after it) replay in creation order so the narrower rule's output wins on the rows both match.
  - `ReapplyRulesCommand` can be invoked on demand and returns updated `matched_count` per rule without requiring a new generation.
- Validation:
  - `CreateRuleCommand` with an empty/whitespace-only `output` is rejected.
  - `CreateRuleCommand` with a `factor_id`/`factor_value_id` pair not belonging to the table is rejected.
  - `CreateRuleCommand` with two pairs naming the same `factor_id` is rejected.
- Edge:
  - `DeleteRuleCommand` for a `rule_id` belonging to another table raises `RuleNotFoundError`.
  - Deleting a rule leaves the `status`/`output` it had set on combinations untouched (no revert).
  - Deleting a factor or a factor value deletes all of that table's rules, not just ones referencing the deleted factor/value.
  - A rule created before the table has ever been generated has `matched_count=0` and is applied once generation completes.
- Regression:
  - Creating/reapplying rules for one table never touches another table's rules or combinations.

## Open Questions

- Per-row rule provenance (so deleting/editing a rule could revert exactly the rows it — and only it — last touched) is not implemented; deletion is "leave rows as last applied." Revisit if users report the current behavior as confusing at higher rule counts.
- Rules currently only ever set `status=possible` + `output` (matching this feature's "fill some factors, provide output" framing). Extending rules to also express `impossible` outcomes is not in this MVP.
