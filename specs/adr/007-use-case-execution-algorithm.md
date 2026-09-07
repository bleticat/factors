# 007. Use Case Execution Algorithm

Date: 2026-05-31

Status: Active

## Context

Application boundaries need a consistent way to execute use cases without knowing how to create units of work, read connections, repositories, handlers, or other shared adapters.

Commands and queries remain semantically different, but callers benefit from one application-facing execution entrypoint.

## Decision

Use a full mediator as the single application-facing entrypoint for executing command and query requests.

Application startup creates long-lived shared adapters, the database port, and an explicit mediator registry.

The mediator registry is explicit typed wiring: each command or query request type has one registered factory that builds its concrete handler from the current execution scope and shared adapters. Registration must be declared in application composition code; do not discover handlers through a dependency injection container, reflection, or string-based routing.

Boundary layers parse input, submit a typed request to the mediator, and serialize the result. They must not initialize repositories, handlers, query classes, connections, or units of work directly.

For command requests, the mediator opens a database unit of work, creates a transaction execution scope, builds the registered command handler, executes it, and lets the unit of work commit on success or roll back on failure.

For query requests, the mediator opens or borrows a read connection, creates a read execution scope, builds the registered query handler, executes it, and returns the read result without a write transaction. Adapters may use read-only transactions or snapshots when they need stable reads.

Version 1 includes lifecycle execution and the guardrails below. Detailed mediator policies for validation, authorization, retries, idempotency, metrics, and error mapping are deferred to future decisions.

## Guardrails

The database port must not expose bounded-context command requests, query requests, handlers, or handler factories.

Handlers must not call the mediator for normal internal work.

Commands and queries remain semantically separate even though callers use one mediator API.

A workflow that needs a write and refreshed data executes a command request first, then a query request.

The follow-up query must read the committed command result from the primary read path unless a future ADR explicitly allows eventual consistency for that workflow.

Boundary layers may reject malformed transport input and serialize protocol responses, but they must not become the home for business validation, authorization policy, retries, idempotency, metrics, or error translation rules.

Business validation and invariants live in command/query handlers, domain objects, or request construction until a later ADR defines a shared validation mechanism.

Do not add mediator middleware or registry behavior for authorization, retries, idempotency, metrics, or error mapping without a separate ADR. Use-case-specific exceptions must be named in the relevant feature spec.

## Alternatives

- Keep boundary layers responsible for creating units of work, repositories, and command/query classes. This is explicit but repeats orchestration and makes lifecycle consistency depend on every caller.
- Use per-context facades instead of a mediator. This reduces dispatch abstraction but gives the application multiple execution entrypoints and less uniform lifecycle handling.
- Use a dependency injection container or string-routed command bus. This reduces manual registration but adds framework behavior or weaker type guarantees.
- Put command and query factories on the database adapter. This centralizes construction but makes the database aware of bounded-context use cases.

## Pros

Boundaries become thin protocol adapters.

Use case lifecycle is consistent across application entrypoints.

Transaction and read-connection rules live in one execution algorithm.

Typed explicit registration keeps dispatch discoverable.

Commands and queries keep separate semantics while sharing one caller-facing API.

## Cons

The mediator and registry add infrastructure.

Handler registration becomes part of application startup.

Dispatch can hide the concrete handler path if registration is not kept clear.

Future middleware needs separate design to avoid turning the mediator into a policy dumping ground.

## Links to Related ADRs

- Depends on: [002. Separate Commands From Queries](./002-separate-commands-from-queries.md)
- Refines: [004. Database Interactions](./004-database-interactions.md)
- Used by: [005. Tests Structure](./005-tests-structure.md)
- Used by: [006. Feature Specification Workflow](./006-feature-specification-workflow.md)
