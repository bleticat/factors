# 008. Merge Repositories and Readers Into One Data-Access Scope

Date: 2026-10-05

Status: Active

## Context

ADR 007 gave `UnitOfWork` every module's write-side repository and
`Database` every module's read-side `...Queries` directly as typed
attributes, removing the composition-root factory layer. In practice this
left two separate access points per use-case method — `uow.tables`/
`uow.rules`/... inside an open `unit_of_work()`, and `database.
tables_queries`/... for reads — each bound to its own session. A read made
through `database.X_queries` inside an open `unit_of_work()` block runs on
a different connection and transaction, so it cannot see that block's own
uncommitted writes; nothing in the types prevented a use case from doing
exactly that, it just happened that none did.

Separately, a read-only use-case method needing more than one read for one
answer (e.g. `list_rules`: a page of rules, an unpaginated pass over every
rule, and a shadowed-match count, all of which must agree) had no way to
get them from one consistent view — ADR 007 dropped `read_scope()` on the
grounds that nothing in a `Queries` adapter writes, which is true but left
such methods composing several independent snapshots instead. This also
forced the `combinations` module to carry a second, DTO-based copy of
`DecisionTable.validate_factor_value_pairs`, purely because its read path
returned a different type than its write path's `uow.tables`.

A newcomer to the codebase asking "if I write some data and then read
something else, how do I use the uow?" got three different answers
depending on which kind of read: a read feeding the write goes through
`uow.X`; a read of the write's own result doesn't happen in-process (ADR
002's command-then-query instead); an unrelated read goes through
`database.X_queries` — a different session, silently.

## Decision

Collapse `UnitOfWork` and the per-call `Queries` access point into one
`DataAccess` object that holds every module's repository *and* reader, all
bound to the same session. `Database` exposes two ways to open one:
`transaction()` (commits on clean exit, rolls back on exception — what
`unit_of_work()` did) and `snapshot()` (always rolls back, replacing the
read-only half of what `read_scope()` did before ADR 007 removed it — for
the one case that still needs it: a read-only method making more than one
call that must agree with each other). Every read and write inside one
`async with` block now sees the same transaction, so a write-then-read is
two lines against the same `db`, and there is one kind of object to read
`.tables`/`.rules`/`.tables_reader`/`.rules_reader` off, not two.

The `@uow` decorator is removed. It saved one line per write method but
type-erased the method's parameter list (`Callable[..., Awaitable[R]]`),
was a third calling convention alongside the manual `async with` some
methods already needed, and the name `uow` collided across the decorator,
its injected keyword parameter, and callers' local variables. Every write
method now opens `async with self._database.transaction() as db:`
explicitly, and every read method opens `snapshot()` explicitly — one
visible pattern instead of three.

Each module's `...Queries` port/adapter is renamed `...Reader`
(`DecisionTableQueries` → `DecisionTableReader`, `SqlAlchemyRuleQueries` →
`SqlAlchemyRuleReader`, etc.), and the attribute instances move from
`database.x_queries` to `db.x_reader` — named for what they are now (one of
two things hanging off a `DataAccess`, next to the repositories) rather
than for ADR 002's command/query vocabulary, which still governs the
separate request/handler split one level up and is untouched by this ADR.

`combinations/service.py`'s `validate_factor_value_pairs(table:
DecisionTableDTO, ...)` is deleted: `combinations/use_cases.py`'s read
methods now load the table via `db.tables.get(table_id)` (the write-side
repository, returning the full `DecisionTable` entity) inside their
`snapshot()`, and call the entity's own `validate_factor_value_pairs` —
safe because nothing in those methods ever calls `save`/`add`/`delete`, so
a read-only repository call has nothing for the snapshot's guaranteed
rollback to undo.

## Alternatives

- Keep `UnitOfWork`/`Database` as two separate attribute namespaces, and
  only document (or lint for) "don't call `database.X_queries` inside an
  open `unit_of_work()` block." Rejected: a convention a reader has to
  remember and nothing enforces is exactly the trap this ADR closes — ADR
  004 already flagged "no automatic dispatch enforcing this" as a known
  cost once, and removing the two namespaces is cheaper than policing the
  gap between them.
- Keep `read_scope()` deleted and leave multi-read use-case methods
  composing several independent `database.X_queries` snapshots. Rejected:
  `list_rules` already demonstrated the failure mode (a page of rules
  tagged with shadow counts computed against a possibly different rule
  set) that a single consistent view exists specifically to prevent.

## Pros

One `async with self._database.transaction()/snapshot()` pattern for every
use-case method, instead of three (the `@uow` decorator, manual `async
with`, and bare reader calls needing no scope at all).

A read that follows a write in the same method is now trivially correct —
same `db`, same session — rather than something that happens to be correct
today because no method does it, with nothing stopping one from getting it
wrong tomorrow.

Multi-read methods (`list_rules`, `list_rule_overlaps`) get one consistent
view across every read in the method, closing the read-skew gap ADR 007's
removal of `read_scope()` opened.

One fewer duplicated validator (`combinations/service.py` deleted) now that
a read-only method can reach the write-side repository's full entity
through the same `db`.

Type checkers (should one be added later) can now see a write method's
real parameter list — the `@uow` decorator's `Callable[..., Awaitable[R]]`
erased it.

## Cons

Every read, even a single-call one, must now open a `snapshot()` —
`database.tables_reader.get(...)` with no scope is no longer available,
since a reader only exists inside an opened `DataAccess`. One extra line on
the simplest read methods.

`DataAccess` is a wider object than either `UnitOfWork` or a lone `Queries`
adapter was — it imports and wires every module's repository and reader
together, continuing (and slightly widening) the ADR 003 exception ADR 007
already acknowledged.

`Reader` doesn't carry ADR 002's "Queries" vocabulary in its name; a reader
coming from ADR 002's own text has to learn that `XReader` is that ADR's
query handler's port, just renamed at the attribute/class level.

## Links to Related ADRs

- Refines: [007. Database Holds Repositories and Queries](./007-database-holds-repositories-and-queries.md)
- Depends on: [002. Separate Commands From Queries](./002-separate-commands-from-queries.md)
- Constrained by: [003. Project Structure](./003-project-structure.md)
