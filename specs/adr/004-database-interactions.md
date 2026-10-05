# 004. Database Interactions

Date: 2026-10-05

Status: Active

## Context

Bounded contexts need persistence without depending on database drivers
or storage details, with transaction boundaries that are hard to get
wrong and cheap to extend — including from workflows that genuinely need
more than one transaction (crash-safe batching, an independent
failure-record commit).

## Decision

A single `Database` port in `shared/` is the only way use-case code
touches persistence. It exposes two ways to open a `DataAccess`:

- `transaction()` — commits on clean exit, rolls back on exception. For a
  write (plus any reads it needs along the way).
- `snapshot()` — always rolls back, never commits. For a read-only method,
  especially one making more than one read that must agree with each
  other.

A `DataAccess` holds every module's write-side repository (`db.tables`,
`db.rules`, `db.combinations`, `db.jobs`) *and* read-side reader
(`db.tables_reader`, ...) bound to the same session — so a read inside one
`async with` block always sees that block's own uncommitted writes, and a
use case opens as many `transaction()`/`snapshot()` blocks as it genuinely
has independent-commit steps (no "one call = one transaction" constraint
enforced by the port). A `DataAccess` is only valid inside the block that
opened it: every attribute on it is replaced with a sentinel the instant
the block exits, so a reference kept past its scope raises immediately
instead of silently running against an already-closed session.

Repositories are write-side ports: load the aggregate whole, mutate in
memory, save whole. Readers are read-side ports for query shapes a
repository's own `get()` can't give cheaply (filtered/paginated lists,
cross-module overlap queries, list-view projections that skip loading a
full aggregate). Where a reader's query would just return the exact same
entity a repository's `get()` already does, there is no separate reader
method — callers use the repository for both reads and writes.

The concrete `SqlAlchemyDatabase`/`SqlAlchemyDataAccess` (in
`shared/adapters/`) are the only place that imports every module's
concrete adapter classes to wire them together — a deliberate exception
to ADR 003's "`shared/` holds no domain behavior," justified because this
app is genuinely one bounded context (the four modules are organizational,
not separate DDD contexts with independent data ownership).

## Alternatives

- Route every call through a composition-root factory function that
  builds a module's command/query service per call from a `UnitOfWork`.
  Rejected: added ceremony for every new cross-module dependency, and
  still needed a separate escape hatch for multi-transaction workflows.
- Give `Database`/`DataAccess` no attribute-level guard and trust callers
  to use a `db` reference only inside its own block. Rejected: a leaked
  reference would silently keep working against a session already
  returned to the pool — worth a loud, immediate failure instead.

## Pros

One pattern (`async with self._database.transaction()/snapshot() as db:`)
for every use-case method; a write-then-read in the same method is
correct by construction (same session, same block); use-case code never
imports SQLAlchemy or a concrete adapter class, only the abstract
repository/reader port each `db` attribute is typed with.

## Cons

`shared/ports/database.py` and `shared/adapters/sqlalchemy_database.py`
depend on every module's ports/adapters — a wider footprint than ADR 003
otherwise calls for. Nothing stops a use-case method from opening the
wrong number of transactions; that's trusted, not enforced.

## Links to Related ADRs

- Depends on: [002. Commands, Queries, and Their Request/Response Contract](./002-commands-queries-and-request-response.md)
- Constrained by: [003. Project Structure](./003-project-structure.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
