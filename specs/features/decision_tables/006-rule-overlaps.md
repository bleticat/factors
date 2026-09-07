# Rule Overlaps

Primary context: `decision_tables`

Affected contexts: `decision_tables`

## Use Case

Rules ([005](./005-output-rules.md)) are replayed in order, and where two rules' assignments both match the same row, the rule later in that order silently wins. As users accumulate more rules on a table, it becomes hard to tell which rows are governed by more than one rule and therefore depend on that ordering — the exact concern flagged in [005](./005-output-rules.md)'s Open Questions. This feature surfaces those rows to the user: given the table's current rules and combinations, show which combinations are matched by two or more rules, which rules those are, and which one currently wins. Since [009](./009-allow-any-order-surface-shadowed-rules.md) removed any restriction on rule content or order, this view — together with 009's per-rule `shadowed_count` — is the primary way a user discovers that a rule isn't taking effect, rather than being an edge case the system otherwise prevents.

## Behavior

- A rule "matches" a combination when every `(factor_id, factor_value_id)` pair in the rule's assignment is present in the combination's own assignment (the same subset check `apply_rule` relies on when it turns a rule into a `BulkPatchCombinationsCommand` filter). A rule with an empty assignment matches every combination.
- This is computed on demand from the table's *current* rules and combinations — nothing new is persisted. It always reflects the live rule set; there is no history of past overlaps or past winners.
- Two or more rules "overlap" on a row when they both match the same combination. For an overlapping row, the **winning rule** is the one that would currently win a reapply: the matching rule with the highest id (creation order), consistent with [005](./005-output-rules.md)'s "later-created rule wins" replay rule.
- Listing overlaps for a table returns every combination matched by 2+ rules, each with the full list of matching rules (id + output, ordered by id ascending — the last entry is the current winner) alongside the combination's own status/output/values. Paginated, ordered by combination id.
- A table with fewer than 2 rules trivially has no overlaps (empty result, no error). A table with 2+ rules but no generated combinations yet also has no overlaps (empty result, no error) — there is nothing for any rule to match.
- This is a pure read: it does not change `matched_count`/`applied_at` on any rule, and does not patch any combination. Reapplying rules ([005](./005-output-rules.md)) remains the only way to make the winning rule's output actually stick on a row.
- The frontend additionally tags each row shown on the Combinations page ([003](./003-review-and-bulk-refine-combinations.md)) with which currently-saved rule(s) match it, using the same subset-match rule against the table's already-fetched rules and each visible row's own assignment — no dedicated endpoint is needed for that per-row tagging since it only concerns rows already on screen.

## Commands and Queries

- Query: `ListRuleOverlapsQuery(table_id, page)` — returns a paginated `CombinationOverlapDTO` list: `{combination: CombinationDTO, matching_rules: [{id, output}, ...]}` ordered by combination id, `matching_rules` ordered by rule id ascending.

## Test Cases

- Success:
  - Two rules on the standard 18-combination table (a broad one, then a narrower one created after it) — `ListRuleOverlapsQuery` returns exactly the rows the narrower rule matches, each entry listing both rules ordered by id (the narrower rule last, i.e. the winner).
  - Three rules where two overlap on a subset and the third's assignment is disjoint from both — the overlap result includes only the rows matched by the two overlapping rules; rows only the disjoint rule matches are excluded.
  - A table-wide default rule (empty assignment) plus one narrow rule — only the narrow rule's matching rows appear in the overlap result (they satisfy 2 rules); rows outside the narrow rule's match satisfy only the default rule (1 rule) and are excluded.
  - Pagination across a page boundary when the overlap set is larger than one page.
- Edge:
  - A table with 0 or 1 rules returns an empty page, no error.
  - A table with 2+ rules but combinations never generated (or generation still in progress) returns an empty page, no error.
- Regression:
  - Overlap results for one table never include another table's rules or combinations.

## Open Questions

None.
