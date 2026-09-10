# 007. Database Holds Repositories and Queries

Date: 2026-09-10

Status: Active

## Context

After the mediator was removed (see the "Remove the mediator" commit), each module's `Commands`/`Queries` service was built per call by a factory function in `app/composition.py`, which constructed concrete repository/query adapters from a `UnitOfWork`/`ReadScope` and injected them as separate constructor parameters. This had two frictions in practice:

Reconsidering this, "one call = one transaction" turned out to be a convention of how `Commands`/`Queries` were built, not a technical constraint of the `Database` port itself — and the factory-function layer added ceremony every time a use case needed a new cross-module repository, or every time a workflow (e.g. the generation worker's batch-then-reapply-rules sequence) needed to open more than one transaction. The existing escape hatches (inject more repos into a `Commands` constructor; write a plain function taking `Database` and call `run_command`/`run_query` per step) worked but required going through `app/composition.py` each time.

## Decision

`Database` and `UnitOfWork` now hold every module's repositories/queries directly as typed attributes, rather than being opaque handles a composition root wires per call:

- `UnitOfWork` (one per open transaction) exposes `tables`, `jobs`, `combinations`, `rules` — each typed as that module's abstract repository port.
- `Database` (one long-lived instance, built once at app startup) exposes `tables_queries`, `combinations_queries`, `rules_queries`, `jobs_queries` — each typed as that module's abstract query port. There is no separate per-call "read scope" — each `Queries` adapter opens and closes its own session per method call, since nothing in a `Queries` adapter ever writes.

Each module's former `Commands` and `Queries` classes merge into one `XUseCases` class per module (`TablesUseCases`, `RulesUseCases`, `CombinationsUseCases`, `GenerationUseCases`), constructed with the app's `Database` directly — not a pre-opened scope. A write method opens `async with self._database.unit_of_work() as uow:` itself and may open more than one such block if it genuinely has independent-commit steps (e.g. the generation worker: one transaction per batch, a separate one to record failure, a separate one to reapply rules after completion — each already justified in spec 002's "Open Questions"). A read method calls straight through to `self._database.x_queries` with no scope-opening at all.

`app/composition.py` is deleted. Its job — knowing every module's concrete `SqlAlchemy*Repository`/`SqlAlchemy*Queries` adapter classes and wiring them together — moves into `app/shared/adapters/sqlalchemy_database.py`'s `SqlAlchemyDatabase` and `app/shared/adapters/sqlalchemy_unit_of_work.py`'s `SqlAlchemyUnitOfWork`, and the type annotations for the attributes above move into `app/shared/ports/database.py` and `app/shared/ports/unit_of_work.py`. `app/shared/execution.py` (`run_command`/`run_query`) is deleted too, since every caller now constructs `XUseCases(database)` directly instead of wrapping a lambda.

This means `shared/ports/database.py` and `shared/ports/unit_of_work.py` now import every module's `ports/` (for the attribute type annotations), and `shared/adapters/sqlalchemy_database.py`/`sqlalchemy_unit_of_work.py` import every module's concrete adapters (to construct them) — a deliberate, acknowledged exception to ADR 003's "shared/ must not hold domain behavior that belongs to one context." This app is genuinely one bounded context (`tables`/`rules`/`combinations`/`generation` are organizational modules, not separate DDD contexts with independent data ownership), so a single `Database`/`UnitOfWork` aggregating all of it isn't crossing a true context boundary — it's the same thing `app/composition.py` already did, just relocated.

## Alternatives

- Keep the composition-root factory-function layer, and only add a "workflow" escape hatch (a plain function taking `Database`, calling `run_command`/`run_query` per step) for the rare multi-transaction case. Smaller change, but `Commands`/`Queries` classes would still need per-call repo/query construction wiring in `composition.py` for every new dependency, and the codebase would carry two different `Commands`/`Queries` shapes (uow-bound vs. Database-bound) side by side.
- Inject `Database` into `Commands`/`Queries` but have each method construct its own concrete adapters inline (`SqlAlchemyRuleRepository(session)`) rather than reading them off `uow`/`database`. Rejected because use-case code would then import SQLAlchemy and concrete adapter classes directly, which is exactly what ADR 004 says use-case code must not do.

## Pros

Adding a new cross-module repository/query dependency to a use case no longer requires touching a separate composition file — it's already available on `uow`/`database`.

Multi-transaction workflows (crash-safe batching, independent-commit steps) are trivial to express: `async with self._database.unit_of_work() as uow: ...`, as many times as a method actually needs, with no factory-function ceremony.

One `UseCases` class per module instead of two — `Commands`+`Queries` merge cleanly now that both take the identical `(database: Database)` constructor.

Use-case code still never imports SQLAlchemy or any concrete adapter class — it only ever sees `uow.tables`/`database.tables_queries` etc., each typed as an abstract port.

## Cons

`shared/ports/database.py` and `shared/ports/unit_of_work.py` now depend on every module's ports, and `shared/adapters/sqlalchemy_database.py`/`sqlalchemy_unit_of_work.py` on every module's adapters — a wider dependency footprint for these files in `shared/` than ADR 003 otherwise calls for, justified above by there being exactly one true bounded context.

The strong, structurally-enforced guarantee "one call = one transaction, no more, no less" (ADR 004's stated Pro of the mediator-era design) is gone — a use-case method is now trusted to open the right number of transactions itself, the same trust already extended to routes/workers under the composition-root design.

## Links to Related ADRs

- Refines: [004. Database Interactions](./004-database-interactions.md)
- Constrained by: [003. Project Structure](./003-project-structure.md) (with the exception noted above)
