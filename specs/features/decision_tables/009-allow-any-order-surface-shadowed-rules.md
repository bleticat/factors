# Allow Any Rule Order; Surface Shadowed Rules

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

[007](./007-reject-more-general-rules.md) rejected creating, editing, or reordering a rule whenever it would become "as general as, or more general than" another rule positioned before it — the idea being to prevent a broad rule from silently clobbering a specific one. In practice this was too restrictive: legitimate reordering and editing got rejected often enough that, from the user's side, changing a rule's order looked like it had no effect at all (compounded by a real display bug — see Regression below — where the overlap view's "current winner" was computed from rule id rather than actual apply order, so even a *successful* reorder didn't visibly change anything).

This feature removes the rejection entirely. Rule order and content are now unrestricted: the user is responsible for arranging rules sensibly, and for noticing when one rule's output is being hidden by another. To make that possible, rules and rows now surface **shadowing** explicitly — which rules currently never (or only partly) take effect, and which specific rows hide them — rather than preventing the situation from arising.

## Behavior

- `CreateRuleCommand` no longer checks a new rule's assignment against existing rules. Any assignment — including a duplicate of an existing rule's, or a table-wide default created after other rules already exist — is accepted and applied immediately, per [005](./005-output-rules.md).
- `UpdateRuleCommand` no longer checks an edited assignment against other rules at the rule's position. Any edit is accepted and re-applied immediately.
- `ReorderRulesCommand` no longer checks the requested order for generality violations — only that it's a valid permutation of the table's rule ids (spec 008). Any order is accepted, persisted, and replayed.
- A rule is **shadowed** on a given row when it matches that row but a rule *later* in apply order (`order_index`) also matches it — that later rule's output is what a reapply actually sets, not this rule's. A rule can be shadowed on some of its rows and not others (a *partial* shadow) or on every row it matches (a *full* shadow, meaning its output currently appears nowhere).
- `ListRulesQuery` reports each rule's `shadowed_count`: how many of that rule's own `matched_count` rows are currently shadowed by *any* later rule (not just a single one — several later rules can jointly shadow rows that none of them alone would fully cover). `shadowed_count <= matched_count` always; `shadowed_count == matched_count > 0` means the rule's output doesn't currently show up anywhere.
- `ListRuleOverlapsQuery` ([006](./006-rule-overlaps.md)) is unaffected in shape, but its `matching_rules` ordering — the mechanism a user actually reads to see "who wins on this row" — is corrected to follow each rule's current `order_index` (apply order) rather than its `id`. Before this fix, a rule that had been dragged to a new position could keep showing the wrong entry as the (bolded) winner, which was indistinguishable from reordering "not working."
- Because nothing is rejected anymore, [006](./006-rule-overlaps.md)'s overlap view and this feature's `shadowed_count` become the primary way a user discovers that a rule isn't taking effect — there is no longer a point at which the system stops them from creating the situation.

## Commands and Queries

- Command: `CreateRuleCommand`, `UpdateRuleCommand`, `ReorderRulesCommand` — generality/order validation removed (see above); otherwise unchanged from specs 005/008.
- Query: `ListRulesQuery(table_id, page)` — `RuleDTO` gains `shadowed_count: int`, computed across *all* of the table's rules (not just the current page) so a rule's shadow status is correct regardless of pagination.
- Query: `ListRuleOverlapsQuery` — `matching_rules` ordering fixed to reflect `order_index`, not `id`.

## Test Cases

- Success:
  - Creating a rule that duplicates an existing rule's assignment succeeds.
  - Creating a table-wide default rule after other rules already exist succeeds and applies to every row (subsequently shadowed on rows any earlier-created-but-now-earlier-in-order rule also covers, per whichever is later in `order_index`).
  - Editing a rule to be broader than a rule positioned before it succeeds.
  - Reordering rules into an order where one shadows another succeeds and reapplies; `ListRulesQuery` reflects the new order.
  - A rule fully shadowed by a single later, broader rule reports `shadowed_count == matched_count`.
  - A rule partially shadowed by a single later, narrower (refining) rule reports `0 < shadowed_count < matched_count`, matching exactly the refining rule's own `matched_count`.
  - A rule shadowed only by the *union* of two later rules — neither of which alone covers all its rows — reports the correct combined `shadowed_count`, not zero and not double-counted.
  - A rule with nothing later in apply order reports `shadowed_count == 0`.
  - After a reorder moves a previously-losing rule to apply last, `ListRuleOverlapsQuery`'s `matching_rules` shows it as the last entry (the winner) on every row they share, matching what a reapply actually sets.
- Edge:
  - `shadowed_count` accounts for rules outside the current page of a paginated `ListRulesQuery` call.
- Regression:
  - The rule creation/update/reorder success paths already covered by specs 005/008 continue to work; only the rejection paths from spec 007 are gone.

## Open Questions

None.
