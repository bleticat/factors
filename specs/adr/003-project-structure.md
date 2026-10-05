# 003. Project Structure

Date: 2026-10-05

Status: Active

## Context

The core should grow by product capability, not by technical layer.

## Decision

Use a feature-based ports-and-adapters structure under the `factors`
package, split into `factors/features/`, `factors/shared/`, and
`factors/entrypoints/`:

- `features/<context>/` — one folder per bounded context (`tables`,
  `rules`, `combinations`, `generation`), each owning its domain
  vocabulary and usually containing:
  - `entities.py` — domain entities, aggregates, and value objects.
  - `use_cases.py` — one `XUseCases` class with one method per use case,
    plus that use case's `Request`/`Response` dataclasses (ADR 002).
  - `ports/` — an abstract write-side repository and an abstract
    read-side reader, plus any value types a reader's query shape
    genuinely needs (not a mirror of an entity).
  - `adapters/` — every concrete implementation of this feature's ports,
    one subfolder per driving/driven technology: `adapters/sqlalchemy/`
    (the repository/reader implementations and the module's ORM row
    mappings) and `adapters/fastapi/` (routes and request-body schemas).
    A FastAPI route handler is exactly as much an adapter as a
    SQLAlchemy repository is — both are a concrete technology plugged
    into the same ports — so neither gets a top-level folder of its own
    alongside `adapters/`.
- `shared/` — cross-context infrastructure only (the `Database` port,
  shared errors, pagination) — never domain behavior belonging to one
  context, with one acknowledged exception: the `Database`/`DataAccess`
  ports must name every feature's port types to type their own
  attributes (see ADR 004).

`entrypoints/` holds the ways this service is actually started — today
just `server.py` (the FastAPI composition root: `create_app()`, CORS,
exception handlers, every router included); a future CLI or worker
process would get its own module here too, each wiring `features/` and
`shared/` together for its own entry path rather than belonging to
either. `factors/config.py` sits directly under `factors/`, alongside
`features/`, `shared/`, and `entrypoints/`, since every one of those
needs it.

## Alternatives

- Organize primarily by technical layer (`domain/`, `use_cases/`,
  `adapters/`). Familiar, but scatters one feature across the tree.

## Pros

New code has an obvious home; domain behavior stays near its ports and
adapters; infrastructure can change behind a port without touching it.

## Cons

More small files than a layered layout; `shared/` needs curating so it
doesn't become a dumping ground.

## Links to Related ADRs

- Used by: [002. Commands, Queries, and Their Request/Response Contract](./002-commands-queries-and-request-response.md)
- Used by: [004. Database Interactions](./004-database-interactions.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
