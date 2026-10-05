# 005. Tests Structure

Date: 2026-10-05

Status: Active

## Context

Core behavior depends on use cases, ports, and persistence boundaries
working together. Most useful tests should verify those boundaries, not
isolated implementation details.

## Decision

Use mostly integration-style tests for core use-case behavior. Each test
gets its own fresh database (migrated via Alembic `upgrade head`, not
`create_all`), destroyed after; tests must not depend on state created by
another test.

Tests call the same `XUseCases(database)` classes application code uses
— built directly over a real `SqlAlchemyDatabase`, never mocked — so they
exercise the same lifecycle as production. Each use-case test focuses on
one command or query `Request`/`Response` pair as the behavior under
test; workflow tests may compose a command and a query to verify
read-after-write, or another explicitly named workflow.

Adapter, repository, migration, and database-port contract tests are
allowed when infrastructure behavior (not use-case behavior) is the
subject. Test folders mirror the bounded-context folders. Shared test
helpers (`tests/helpers.py`) are allowed to cut setup noise but must never
hide the use-case call under test.

## Alternatives

- Prefer isolated unit tests with mocked repositories. Faster, but can
  miss persistence, mapping, and transaction-scope bugs.
- Reuse one database across tests. Faster, but risks order-dependent
  tests and hidden shared state.

## Pros

Tests exercise the same ports and use-case lifecycle as production code;
fresh databases keep them independent and repeatable.

## Cons

Slower than pure unit tests; per-test database setup adds boilerplate.

## Links to Related ADRs

- Depends on: [003. Project Structure](./003-project-structure.md)
- Depends on: [004. Database Interactions](./004-database-interactions.md)
