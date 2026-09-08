# 004. Database Interactions

Date: 2026-05-30

Status: Active

## Context

Bounded contexts need persistence without depending on database drivers or storage details.

Writes also need consistent transaction boundaries. Reads need room for optimized query shapes.

Boundary layers (API routes, the background worker, the startup sweep, tests) should not construct repositories or adapters directly — the composition root is the one place that knows concrete adapter classes.

## Decision

Access persistence through a shared core `Database` port and the composition root's factory functions.

The database is a port in `shared/`. It owns access to persistence resources but must not expose module-specific command/query types or service classes.

For writes, the caller opens a `unit_of_work()`, passes it to the relevant module's `build_*_commands` factory (in `app/composition.py`) to get a fully-wired `Commands` service, and calls a method on it.

The unit-of-work lifecycle owns transaction behavior: commit on success, rollback on failure.

For reads, the caller opens a `read_scope()`, passes it to the module's `build_*_queries` factory, and calls a method on the resulting `Queries` service. Adapters may use read-only transactions or connection snapshots when needed, but queries must not own commit or rollback of business writes — `read_scope()` always rolls back on exit, even if a query mistakenly writes through it.

A command followed by a query in the same workflow must read the committed result of that command from the primary read path. If a later decision introduces read replicas, projections, or async read models, that decision must state where read-your-writes is required and where eventual consistency is acceptable.

Repositories are write-side ports for loading, saving, and deleting domain entities inside a transaction.

Queries are read-side ports and query services. They may use optimized joins, projections, filters, or read models without changing command services or repository APIs.

Concrete database code lives in adapters. Domain code, command/query services, and the composition root's factory functions depend on ports, not adapter internals — except that a module's own adapters depend on that module's own concrete adapter classes directly, which is expected (see ADR 003's "ports/entities cross module lines, adapters don't").

## Alternatives

- Let command/query services use database drivers directly. This is simpler at first but couples core behavior to storage details.
- Manage transactions in boundary layers by hand at every call site. This gives callers control but makes transaction safety depend on each call site remembering to do it correctly.
- Put module-specific factories directly on the concrete database adapter. This keeps the composition root smaller but turns the database into a use-case registry.

## Pros

Write behavior gets automatic transaction boundaries.

Command/query services stay focused on use-case behavior.

Queries can be tuned for read needs without complicating writes.

The database port stays small and does not need to know every module's use cases.

Database technology can change behind adapters.

Tests can use the same database port and composition-root factories as production code.

## Cons

There are more abstractions than direct database calls.

Read and write paths may duplicate some mapping code.

Callers must remember to open the right kind of scope (`unit_of_work()` vs `read_scope()`) — there is no automatic dispatch enforcing this; see the "Alternatives" in the (now-removed) mediator-based design this replaced.

Read-after-write behavior needs explicit care if optimized read models or replicas are introduced later.

## Links to Related ADRs

- Depends on: [002. Separate Commands From Queries](./002-separate-commands-from-queries.md)
- Constrained by: [003. Project Structure](./003-project-structure.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
