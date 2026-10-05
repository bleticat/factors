# 002. Commands, Queries, and Their Request/Response Contract

Date: 2026-10-05

Status: Active

## Context

Core behavior has writes and reads, and each needs a stable, typed shape
for its inputs and outputs — not a hand-rolled parameter list on one side
and a hand-copied result type on the other.

## Decision

Each bounded context exposes one `XUseCases` class (e.g. `TablesUseCases`)
with one method per use case. A **command** method changes state and
enforces invariants; a **query** method only reads. Every method takes
exactly one `...Request` dataclass (bundling its inputs) and returns
exactly one `...Response` dataclass.

A `Response` wraps the resulting domain entity/aggregate directly (e.g.
`CreateRuleResponse.rule: Rule`) rather than a hand-copied mirror of its
fields — there is no separate "DTO"/"Ref" type family. A field that's
genuinely new information the method computed (a count, a `kind`
discriminator) and isn't a view of any entity stays a plain `Response`
field, since there's nothing to wrap.

Boundary layers (API routes, the worker, tests) construct a `Request` and
call the method. A query that follows a command in the same workflow
reads that command's already-committed result from the primary read
path — this app has no read replicas or async read models, so there's no
eventual-consistency case to handle.

## Alternatives

- Give each read its own "DTO" type distinct from the write-side entity.
  Rejected: once a read and a write return the same aggregate shape, a
  second type mirroring it field-for-field is pure upkeep cost with no
  behavior behind it.

## Pros

One typed way in and out of every use case — call sites can't drift into
ad hoc, unordered kwargs, and callers/tests see exactly one shape to
construct and one to read.

## Cons

Every method gets a small `Request`/`Response` pair, even a trivial
single-field one.

## Links to Related ADRs

- Used by: [003. Project Structure](./003-project-structure.md)
- Used by: [004. Database Interactions](./004-database-interactions.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
