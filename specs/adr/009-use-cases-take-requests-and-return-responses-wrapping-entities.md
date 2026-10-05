# 009. Use Cases Take Requests and Return Responses Wrapping Entities

Date: 2026-10-05

Status: Active

## Context

After ADR 008 unified repositories and readers under one `DataAccess`,
each module still carried two parallel families of small result types for
the same underlying concept: a reader-side `...DTO` (used only for reads)
and a `...Ref`/`...Result` type (hand-built by write methods per ADR 002's
guidance against "return full read-side projections from every command").
For every aggregate whose read and write paths now return the identical
entity (the point of ADR 008), these had become redundant:
`DecisionTableDTO`/`FactorDTO`/`FactorValueDTO` duplicated
`DecisionTable`/`Factor`/`FactorValue` field-for-field; `RuleDTO`
duplicated `Rule` plus two extra fields (`created_at`, `shadowed_count`)
that existed only because the entity didn't carry them yet;
`CombinationDTO`/`CombinationValueDTO` duplicated
`Combination`/`CombinationValue` minus two internal fields; `GenerationJobDTO`
and `GenerationJobRef` were byte-for-byte identical shapes under two names.

Separately, use-case methods took their business parameters as a flat,
growing kwarg list (e.g. `update_rule(table_id, rule_id, output=None,
title=None, title_set=False, factor_values=None, factor_values_set=False)`)
— which ADR 002 had already called for bundling into a "typed request
shape" at the boundary, a decision the post-mediator refactors (ADR
007/008) quietly dropped in favor of individual parameters.

## Decision

1. Every reader port returns the module's real entity/aggregate wherever
   its shape doesn't genuinely differ from the write-side repository's,
   deleting the `...DTO` type. Where a reader's own `get()` had become
   byte-for-byte identical to the repository's `get()` (both returning the
   same entity), the reader method is deleted outright — callers use
   `db.tables.get()`/`db.rules.get()`/etc. for both reads and writes. A
   reader keeps a distinct result type only where the query is a genuine
   projection a full entity load couldn't give cheaply —
   `DecisionTableSummary` (a list-view count instead of every factor's
   values) is the one surviving case, and it's deliberately not an entity.

2. Every `XUseCases` public method takes exactly one `...Request`
   dataclass and returns exactly one `...Response` dataclass. A `Response`
   wraps the operation's resulting entity/aggregate directly
   (`CreateRuleResponse.rule: Rule`) rather than hand-copying its fields
   into a parallel shape — the `...Ref`/`...Result` family
   (`DecisionTableRef`, `FactorRef`, `RuleRef`, `CombinationRef`,
   `GenerationJobRef`, `RuleApplyRef`, `EvaluateResult`, `BulkPatchResult`,
   `ReapplyRulesResult`, ...) is gone. A field that's genuinely new
   information the use case computed, not a view of any entity
   (`matched_count`/`updated_count` from a bulk patch, the `kind`
   discriminator from evaluate), stays a plain `Response` field — there's
   nothing to wrap.

3. `apply_rule` (the shared rule-application helper both `create_rule` and
   `reapply_rules` call) now returns the `Rule` it was given, with
   `matched_count`/`applied_at` updated to the outcome, instead of a
   separate `RuleApplyRef` — those two fields are exactly what changed,
   and the entity already carries them.

4. HTTP routes construct the `Request` from the parsed body/path params
   and return `response.<field>` (the wrapped entity, or the response's
   sole other field) rather than the `Response` object itself, so each
   endpoint's JSON keeps its existing top-level shape. The change this
   causes is additive where an entity happens to carry more fields than
   its old hand-trimmed `Ref`/`DTO` did (e.g. a patched combination's JSON
   now also includes `generation_job_id`/`signature`/`values`) — never a
   removed or renamed top-level key — with one deliberate exception:
   `POST /rules/reapply` and `/rules/reorder` now return `{"rules": [...]}`
   (full `Rule` objects) in place of the old `{"results": [{"rule_id",
   "matched_count", "applied_at"}, ...]}`. Checked against the frontend
   first (see Cons) before accepting that one.

## Alternatives

- Keep each reader's own DTO and give write methods a `Response` wrapping
  that DTO instead of the entity. Rejected: the DTO was the redundancy
  being removed — reintroducing it as the `Response`'s payload just moves
  the duplication rather than deleting it.
- Only bundle `Request` objects for methods that already took several
  optional parameters, leaving single-id reads (`get_decision_table
  (table_id)`) as bare parameters. Rejected for consistency: one calling
  convention for every use-case method is easier to learn than two, and
  the ceremony cost of a one-field `Request` is small.

## Pros

One request/response-shaped way in and out of every use-case method,
matching ADR 002's original "typed request shape" intent, which had
drifted since the mediator was removed.

Deleted the `XDTO`/`XRef`/`XResult` families outright across all four
modules, plus the `to_ref`/`app/generation/service.py` glue that only
existed to build them — one fewer type family to keep in sync with the
entity it mirrored, and `app/combinations/service.py`'s duplicate
`validate_factor_value_pairs` (kept alive only because the read path
returned a different type than `DecisionTable`) is gone with it.

A handful of reader methods that had become byte-for-byte duplicates of
their repository's own `get()` are gone too — `RuleReader.get`,
`CombinationReader.get`, `GenerationJobReader.get`,
`DecisionTableReader.get` were all unused or redundant and are deleted.

## Cons

Every `Response` is a new, if small, dataclass — a one-field wrapper
(`CreateRuleResponse.rule: Rule`) around something a method could
otherwise just return directly. Callers always unwrap one level
(`response.rule`, `response.table`); routes do this once per endpoint,
tests do it once per call site.

`/rules/reapply`/`/rules/reorder` change field-level response content
(full `Rule` vs. the old slim per-rule shape) — confirmed the frontend
only ever triggers these as cache-invalidating mutations and never reads
a field off the result, so this is safe today, but it's the one place
this ADR's "additive-only" JSON promise has an exception worth
remembering if a future caller starts reading that field.

A `Response` wrapping a full entity exposes some fields over HTTP that
their old hand-trimmed type intentionally left out (e.g. a combination's
`generation_job_id`/`signature`). Harmless today — nothing sensitive, and
the frontend already tolerates unknown fields — but worth a conscious
check if a future entity field is something that genuinely shouldn't
leave the service.

## Links to Related ADRs

- Refines: [008. Merge Repositories and Readers Into One Data-Access Scope](./008-merge-repositories-and-readers-into-one-data-access-scope.md)
- Refines: [002. Separate Commands From Queries](./002-separate-commands-from-queries.md)
