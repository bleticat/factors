# 002. Separate Commands From Queries

Date: 2026-05-30

Status: Active

## Context

Core behavior has writes and reads. Writes enforce rules and change state. Reads retrieve data for views, decisions, and integrations.

Mixing them hides intent and can push orchestration, transaction handling, or read shaping into boundary code.

## Decision

Separate command requests from query requests inside each bounded context.

Command requests are data-only inputs for state-changing use cases. They describe the requested business change but do not perform it.

Command handlers implement write behavior. They enforce rules, call needed ports, change state, and leave the system valid.

Query requests are data-only inputs for read use cases. They describe the requested read shape, filters, or lookup.

Query handlers implement read behavior. They can return entities, projections, or read models and may be optimized for specific read needs without reshaping command handlers.

Boundary layers submit typed command or query requests to the application mediator. They must not coordinate repositories, instantiate handlers, or duplicate command rules.

When a workflow needs a write and refreshed data, run a command request, then a query request. The follow-up query reads committed command results from the primary read path unless a later ADR explicitly introduces eventually consistent read models or replicas.

## Alternatives

- Let boundary layers coordinate repositories directly. This reduces use-case types but spreads business rules and transaction assumptions into UI or adapter code.
- Use one request kind for both reads and writes. This gives one interaction style but hides whether a call changes state.
- Return full read-side projections from every command. This can simplify callers but couples write use cases to screen-specific read needs.

## Pros

Write behavior stays small and rule-focused.

Queries can evolve for performance, screens, reports, and integrations.

Read models can change without reshaping command APIs.

Tests can target write and read contracts separately while exercising the shared mediator lifecycle.

## Cons

Small features get some extra ceremony.

Some workflows need both a command request and a query request.

The term `command` now refers to a request type; use `command handler` when referring to the behavior implementation.

## Links to Related ADRs

- Used by: [003. Project Structure](./003-project-structure.md)
- Used by: [004. Database Interactions](./004-database-interactions.md)
- Refined by: [007. Use Case Execution Algorithm](./007-use-case-execution-algorithm.md)
