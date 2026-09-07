# Reject More-General Rules

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Rules ([005](./005-output-rules.md)) replay in creation order, and the later-created rule silently wins wherever two rules' assignments both match a row. That is a reasonable default when a user is deliberately *refining* an existing rule — e.g. "Browser=Safari" is unsupported in general, except when "Browser=Safari, OS=iOS" — but it is a trap when a user later adds a *broader* rule than one they already have: the new broad rule would quietly overwrite the earlier, carefully-scoped rule's output on every row they share, with nothing in the UI calling that out at the moment it happens. This feature turns that specific ordering mistake into a rejected conflict at creation time, while keeping the "refine a general rule with a more specific one" workflow — the common, intended case — unaffected.

## Behavior

- Compare rule assignments as sets of `(factor_id, factor_value_id)` pairs. Rule A **is at least as general as** rule B when A's assignment set is a subset of B's assignment set (`⊆`) — every row B matches, A also matches. This includes the case where the two assignments are equal (neither refines the other).
- Rule A **refines** rule B when B's assignment is a *strict* subset of A's (`B ⊊ A`) — A matches a strict subset of B's rows. This is the allowed direction: it is how a user "carves out an exception" from a broader default.
- Two assignments are **incomparable** when neither is a subset of the other (e.g. they constrain different factors). This is unaffected by this feature — incomparable rules may still overlap on some rows (see [006](./006-rule-overlaps.md)'s overlap view), but creating one is never blocked by the check here.
- `CreateRuleCommand` rejects a new rule if it is at least as general as any rule that already exists for the table — the whole creation is rejected outright: nothing is persisted, and no combination is patched (contrast with a rule that *is* allowed to be created, which applies immediately per [005](./005-output-rules.md)).
- Because an empty assignment (`[]`) is a subset of every other assignment, it can only ever be the table's *first* rule — attempting to add a table-wide default after any other rule already exists is always rejected as "more general". Adding an empty-assignment rule as the very first rule for a table is unaffected (nothing exists yet to conflict with).
- This check only runs at `CreateRuleCommand` time, against the table's currently-existing rules. It is not re-run by `ReapplyRulesCommand` — replay only ever re-executes rules that already passed this check pairwise against every rule that existed before them, so the whole table's rule set stays consistent by induction; there is nothing new to validate on replay.
- Deleting a rule ([005](./005-output-rules.md)) never needs to re-validate the remaining rules against each other: removing a rule can only remove constraints another rule might have conflicted with, never introduce a new one.

## Commands and Queries

- Command: `CreateRuleCommand(table_id, factor_values, output)` — in addition to its existing validation ([005](./005-output-rules.md)), now also checks the new assignment against every existing rule for `table_id`; raises `RuleTooGeneralError(conflicting_rule_id)` if any existing rule's assignment is a superset of (or equal to) the new one's, identifying the conflicting existing rule.

## Test Cases

- Success:
  - Creating a broad rule (`Browser=Chrome`) then a strictly narrower one (`Browser=Chrome, OS=Windows`) succeeds — refining is allowed.
  - Creating two rules with incomparable assignments (`Browser=Chrome`; `OS=Windows`) both succeed, in either order.
  - Creating the very first rule for a table with an empty assignment succeeds (nothing exists yet to conflict with).
- Validation:
  - Creating a rule whose assignment exactly duplicates an existing rule's assignment is rejected.
  - Creating a broader rule (`Browser=Chrome`) after a narrower one already exists (`Browser=Chrome, OS=Windows`) is rejected, naming the narrower rule as the conflict.
  - Creating a rule with an empty assignment after any other rule already exists for the table is rejected.
  - The conflict check is scoped to one table: a specific rule on table A never blocks an unrelated default rule on table B.
- Edge:
  - A rejected `CreateRuleCommand` persists no rule and leaves every existing rule's `matched_count`/`applied_at` untouched.

## Open Questions

None.
