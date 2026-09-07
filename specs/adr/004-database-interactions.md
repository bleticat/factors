# 004. Database Interactions

Date: 2026-05-30

Status: Active

## Context

Bounded contexts need persistence without depending on database drivers or storage details.

Writes also need consistent transaction boundaries. Reads need room for optimized query shapes.

Use case execution now goes through a mediator, so boundary layers should not create units of work, connections, repositories, or handlers directly.

## Decision

Access persistence through shared core ports and the mediator execution algorithm.

The database is a port in `shared/`. It owns access to persistence resources but must not expose bounded-context command requests, query requests, handlers, or handler factories.

For command requests, the mediator opens a unit of work, creates a transaction execution scope, builds the registered command handler, and executes it inside that scope.

The unit-of-work lifecycle owns transaction behavior: commit on success, rollback on failure.

For query requests, the mediator opens or borrows a read connection, creates a read execution scope, builds the registered query handler, and executes it without a write transaction. Adapters may use read-only transactions or connection snapshots when needed, but queries must not own commit or rollback of business writes.

A command followed by a query in the same workflow must read the committed result of that command from the primary read path. If a later decision introduces read replicas, projections, or async read models, that decision must state where read-your-writes is required and where eventual consistency is acceptable.

Repositories are write-side ports for loading, saving, and deleting domain entities inside a transaction.

Queries are read-side ports and handlers. They may use optimized joins, projections, filters, or read models without changing command handlers or repository APIs.

Concrete database code lives in adapters. Domain code, handlers, and mediator factories depend on ports, not adapter internals.

## Alternatives

- Let handlers use database drivers directly. This is simpler at first but couples core behavior to storage details.
- Manage transactions in boundary layers. This gives callers control but makes transaction safety depend on each call site.
- Put context-specific handler factories directly on concrete database adapters. This keeps mediator wiring smaller but turns the database into a use case registry.

## Pros

Write behavior gets automatic transaction boundaries.

Handlers stay focused on use case behavior.

Queries can be tuned for read needs without complicating writes.

The database port stays small and does not need to know every bounded-context use case.

Database technology can change behind adapters.

Tests can use the same mediator and database ports as production code.

## Cons

There are more abstractions than direct database calls.

Read and write paths may duplicate some mapping code.

Handler factories need explicit registration during application startup.

Read-after-write behavior needs explicit care if optimized read models or replicas are introduced later.

## Links to Related ADRs

- Depends on: [002. Separate Commands From Queries](./002-separate-commands-from-queries.md)
- Constrained by: [003. Project Structure](./003-project-structure.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
- Refined by: [007. Use Case Execution Algorithm](./007-use-case-execution-algorithm.md)
