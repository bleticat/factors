# 003. Project Structure

Date: 2026-10-05

Status: Active

## Context

The core should grow by product capability, not by technical layer.

## Decision

Use a feature-based ports-and-adapters structure under the `factors`
package, split into `factors/features/` and `factors/shared/`:

- `features/<context>/` — one folder per bounded context (`tables`,
  `rules`, `combinations`, `generation`), each owning its domain
  vocabulary and usually containing:
  - `entities.py` — domain entities, aggregates, and value objects.
  - `use_cases.py` — one `XUseCases` class with one method per use case,
    plus that use case's `Request`/`Response` dataclasses (ADR 002).
  - `ports/` — an abstract write-side repository and an abstract
    read-side reader, plus any value types a reader's query shape
    genuinely needs (not a mirror of an entity).
  - `adapters/` — concrete (SQLAlchemy) implementations of those ports
    and the module's ORM row mappings.
  - `api/` — FastAPI routes and request-body schemas.
- `shared/` — cross-context infrastructure only (the `Database` port,
  shared errors, pagination) — never domain behavior belonging to one
  context, with one acknowledged exception: the `Database`/`DataAccess`
  ports must name every feature's port types to type their own
  attributes (see ADR 004).

`factors/main.py` (the FastAPI composition root) and `factors/config.py`
sit directly under `factors/`, outside both `features/` and `shared/`,
since they wire the two together rather than belonging to either.

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
