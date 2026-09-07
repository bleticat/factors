# Edit and Reorder Rules

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Rules ([005](./005-output-rules.md)) could originally only be created and deleted — fixing a typo in an output, adding a title, or narrowing an assignment meant deleting the rule and recreating it, losing its position in the apply order. This feature adds in-place editing and explicit, drag-and-drop-friendly reordering.

An earlier version of this feature also rejected edits/reorders that would make one rule "too general" relative to another ([007](./007-reject-more-general-rules.md)). That rejection is gone as of [009](./009-allow-any-order-surface-shadowed-rules.md): any assignment and any order is allowed, and a rule left hidden behind a more general one is surfaced as **shadowed** rather than blocked. This document now describes only the edit/reorder mechanics; see 009 for the shadowing behavior itself.

## Behavior

- A rule's position is explicit: `order_index`, an integer assigned `len(existing rules)` (append at the end) when a rule is created. Every place that used to mean "creation order" — replay order, `ListRulesQuery`'s order — means **order by `order_index`** instead of by `id`. For rules that predate this feature, `order_index` was backfilled to match their existing id-based order exactly.
- `UpdateRuleCommand` edits an existing rule's `output`, `title`, and/or `assignment` (`factor_values`) — any subset of them, independently and optionally — without changing its `order_index`:
  - Changing `output` and/or `factor_values` immediately re-applies the rule (same as creation — the same set-based update, using the rule's current assignment as the filter), refreshing `matched_count`/`applied_at`. As with delete ([005](./005-output-rules.md)), rows the rule no longer matches after a narrower/relocated assignment keep whatever output they were last set to — there's still no revert.
  - Changing only `title` does not re-apply anything (title never affects matching).
  - The same assignment/duplicate-factor/table-membership validation as `CreateRuleCommand` applies to an edited assignment. There is no generality check — any assignment is accepted regardless of how it relates to other rules' assignments.
- `ReorderRulesCommand` takes a complete new ordering for a table — every one of its rules' ids, in the desired order — used by the "Saved rules" list's drag-and-drop:
  - Rejects the request if the given ids aren't exactly the table's current rule ids (no subset, no extras, no duplicates) — a reorder is a permutation, not a partial move. This is the only validation; any resulting order is otherwise accepted.
  - On success, persists the new `order_index` for every rule (0-based, by position in the given list) and immediately replays all of them in the new order (same effect as `ReapplyRulesCommand`), returning the per-rule apply results.
- Editing or reordering never changes a rule's `id`, `created_at`, or which table it belongs to.

## Commands and Queries

- Command: `UpdateRuleCommand(table_id, rule_id, output=None, title=None, title_set=False, factor_values=None, factor_values_set=False)` — raises `RuleNotFoundError` if `rule_id` doesn't belong to `table_id`, `EmptyNameError` for a blank `output`, and the same assignment-validation errors as `CreateRuleCommand` for a bad `factor_values`. Returns `RuleRef(id, matched_count, applied_at)`.
- Command: `ReorderRulesCommand(table_id, ordered_rule_ids)` — raises `DecisionTableNotFoundError` if the table doesn't exist and `InvalidRuleOrderError` if `ordered_rule_ids` isn't exactly a permutation of the table's rule ids. Returns the same shape as `ReapplyRulesCommand`: `ReapplyRulesResult(results: [RuleApplyRef])`.
- Query: `ListRulesQuery`/`ListRuleOverlapsQuery` (unchanged signatures) order by `order_index` instead of `id`.

## Test Cases

- Success:
  - Editing a rule's `output` updates already-matched rows to the new output and refreshes `matched_count`/`applied_at`, without changing its position relative to other rules.
  - Editing only a rule's `title` does not change `matched_count`/`applied_at`.
  - Narrowing a rule's assignment succeeds and re-applies to the smaller matching set; rows no longer matched keep their prior output.
  - Editing a rule's assignment to be more general than, or a duplicate of, another rule's assignment succeeds (no rejection) — see [009](./009-allow-any-order-surface-shadowed-rules.md) for how that's surfaced.
  - Reordering rules into an arbitrary new order succeeds, persists the new `order_index` values, and re-applies all of them so the new order's winner is reflected on matching rows immediately.
  - `ListRulesQuery` reflects rules in `order_index` order after a reorder, not creation order.
- Validation:
  - `UpdateRuleCommand` with a blank `output` is rejected.
  - `ReorderRulesCommand` with a list that omits one of the table's rules, includes a foreign rule id, or repeats an id is rejected with `InvalidRuleOrderError`; nothing is persisted.
- Edge:
  - `UpdateRuleCommand` for a `rule_id` belonging to another table raises `RuleNotFoundError`.
  - A table with rules created before this feature existed replays/lists identically to before until one of its rules is actually edited or reordered (backfilled `order_index` matches prior id order).
- Regression:
  - Editing or reordering rules on one table never touches another table's rules, combinations, or order.
  - The success/validation/edge cases already covered by spec 005 for `CreateRuleCommand`/`DeleteRuleCommand`/`ReapplyRulesCommand` are unaffected by the presence of `order_index`.

## Open Questions

None.
