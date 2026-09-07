# 005. Tests Structure

Date: 2026-05-30

Status: Active

## Context

Core behavior depends on command requests, query requests, handlers, mediator execution, and persistence boundaries working together.

Most useful tests should verify those boundaries, not isolated implementation details.

## Decision

Use mostly integration-style tests for core use-case behavior.

Each test initializes its own database and destroys it within the test lifecycle. Tests must not depend on state created by another test.

Tests should prefer executing command and query requests through the mediator, so they exercise the same lifecycle as application code.

Each use-case behavior test should focus on one command request or one query request as the behavior under test. Workflow tests may compose a command and a query when verifying read-after-write behavior or another explicitly specified workflow.

Handler-level tests are allowed when useful, but use-case behavior tests must not call adapters or repositories directly as the behavior under test.

Adapter, repository, migration, and database-port contract tests are allowed when infrastructure behavior is the subject of the test. These tests should still use isolated database state and should not duplicate use-case behavior tests.

Test folder structure should mirror bounded-context separation. A context's tests live in the matching test module or folder.

Shared test helpers are allowed when they reduce setup noise, but they must not hide the command or query request being tested.

## Alternatives

- Prefer isolated unit tests with mocked repositories. This is faster but can miss persistence, mapping, mediator wiring, and transaction bugs.
- Test mostly through the UI or Tauri boundary. This verifies full flows but makes failures harder to localize.
- Reuse one database across tests. This is faster but risks order-dependent tests and hidden shared state.

## Pros

Tests exercise the same core ports and mediator lifecycle used by application code.

Fresh databases keep tests independent and repeatable.

Mirrored folders make test ownership obvious.

Command and query tests stay aligned with the core architecture.

## Cons

Integration-style tests are slower than pure unit tests.

Per-test database setup adds boilerplate.

Helpers need discipline so tests still show the behavior under test clearly.

Infrastructure contract tests add another test category to maintain.

## Links to Related ADRs

- Depends on: [003. Project Structure](./003-project-structure.md)
- Depends on: [004. Database Interactions](./004-database-interactions.md)
- Used by: [006. Feature Specification Workflow](./006-feature-specification-workflow.md)
- Depends on: [007. Use Case Execution Algorithm](./007-use-case-execution-algorithm.md)
