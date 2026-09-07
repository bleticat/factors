# 006. Feature Specification Workflow

Date: 2026-05-30

Status: Active

## Context

We are moving to spec-driven development. New features need a written use case before code so tests and implementation have a shared target.

Use cases are now invoked through typed command and query requests handled by the mediator.

## Decision

Put feature specs in `specs/features/`.

Use `specs/features/000-template.md` as the starting point for new feature specs.

Mirror bounded-context folders inside `specs/features/`. A feature spec belongs to the primary context it changes. Cross-context specs should name affected contexts and split only when they describe separate use cases.

Feature workflow:

1. Write or update the feature spec.
2. List material test cases and coverage obligations before implementation.
3. Add tests matching the listed cases.
4. Implement through command/query requests, handlers, ports, mediator registration, and adapters.
5. Keep the spec and tests in sync when behavior changes.

Suggested feature spec structure:

- `# Feature Name`
- `## Use Case`
- `## Behavior`
- `## Commands and Queries`
- `## Test Cases`
- `## Open Questions`

`## Commands and Queries` should name the command and query requests involved, their expected results, and any mediator-visible lifecycle expectations.

`## Test Cases` is required. It should list the material scenarios the implementation is expected to cover, including success, validation, edge, regression, lifecycle, and transaction cases when relevant. The list can link to concrete tests after they are added and does not need to enumerate trivial permutations.

## Alternatives

- Treat tests as the only executable specification. This avoids duplicate documents but can make product intent harder to review before implementation.
- Write specs after implementation. This captures final behavior but loses the planning and review benefits of spec-driven work.
- Store feature specs beside code. This keeps specs near implementation but can make product behavior harder to scan as a set.

## Pros

Features start from behavior instead of code shape.

The material test-case list makes scope visible before implementation.

Mirrored folders keep specs aligned with bounded contexts.

Specs, tests, and code can be reviewed together.

## Cons

Writing the spec adds upfront work.

The material test-case list must be maintained as behavior changes.

Cross-context use cases may require judgment about spec ownership.

## Links to Related ADRs

- Depends on: [003. Project Structure](./003-project-structure.md)
- Depends on: [005. Tests Structure](./005-tests-structure.md)
- Depends on: [007. Use Case Execution Algorithm](./007-use-case-execution-algorithm.md)
