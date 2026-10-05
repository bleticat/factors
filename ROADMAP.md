# Roadmap to 1.0

Where this project stands today: a FastAPI + SQLAlchemy + SQLite backend
(ports/adapters architecture, documented in `specs/adr/`, 128 passing
tests, `ruff` clean) behind a React frontend, runnable locally via Docker
Compose. There is no authentication, no CI, no license, no deployment
story beyond the local dev loop, and zero frontend tests. This file tracks
what's left to call it 1.0 and put it in front of other people — as a
public repo, as something deployed somewhere real, or both.

Check items off as they land; add items as they turn up. Nothing here is
implemented yet unless marked done.

## Decisions needed first

A handful of items below are blocked on a choice only you can make. Worth
settling these before working through the milestones, since several
checklist items change shape depending on the answer.

- **License.** Open-sourcing needs one. MIT/Apache-2.0/BSD-3 are the usual
  permissive defaults for a tool like this; (A)GPL if you want anything
  built on it to stay open. Blocks adding `LICENSE` and listing the repo
  publicly.
- **Single-user or multi-user?** Today every decision table is global —
  there's no user/tenant concept anywhere in the data model, and no
  authentication. If this stays a self-hosted, single-user tool, that's
  fine as-is (document "put it behind your own reverse proxy / VPN" and
  move on). If it's meant to serve multiple people with separate data,
  that's the single biggest item on this list: real auth, a `user_id`/
  tenant column on the aggregate tables, and every use case scoped by it.
- **Deployment target.** Docker Compose on a single host is enough for
  self-hosting. A specific PaaS (Fly.io, Railway) or cloud target changes
  what "production config" below actually means.
- **SQLite or Postgres?** SQLite (already in place, WAL mode, fine for one
  instance) is zero further work. Postgres is needed only if you'll ever
  run more than one backend instance, or want managed backups/HA — treat
  it as an explicit migration item (below), not a default.

## Milestone 1 — Open-source hygiene

- [ ] `LICENSE` (per the decision above)
- [ ] `CONTRIBUTING.md` — how to run the backend/frontend, test and lint
      commands, branch/PR conventions (`specs/adr/005-tests-structure.md`
      already covers the testing half; this can mostly link to it)
- [ ] `CODE_OF_CONDUCT.md` (e.g. Contributor Covenant)
- [ ] `SECURITY.md` — how to privately report a vulnerability
- [ ] `.github/ISSUE_TEMPLATE/` + `PULL_REQUEST_TEMPLATE.md`
- [ ] `CHANGELOG.md`, and settle on semver going forward
- [ ] One pass on `README.md` for a stranger landing on the repo cold
      (current one is solid on "what is this" and "run it locally";
      revisit once the above exist so it links out to them)

## Milestone 2 — CI

- [ ] GitHub Actions: backend — `uv run ruff check`, `uv run ruff format
      --check`, `uv run pytest`
- [ ] GitHub Actions: frontend — `npm run lint`, `tsc -b`, `npm run build`
- [ ] Branch protection requiring CI green before merge (repo setting)
- [ ] Dependabot/Renovate for dependency updates (optional, but cheap)

## Milestone 3 — Backend production-readiness

- [ ] `/health` liveness endpoint — nothing calls one today
- [ ] `.env.example` documenting every `FACTORS_*` setting
      (`database_url`, `max_combinations`, `generation_batch_size`,
      `cors_origins`) — settings are already env-driven
      (`backend/factors/config.py`), just undocumented
- [ ] Set the real deployed frontend origin in `FACTORS_CORS_ORIGINS` for
      prod (defaults to `localhost` today, correctly, for dev)
- [ ] If multi-user (per decision above): auth + per-tenant data isolation
- [ ] Rate limiting / request size limits for a publicly-reachable
      deployment — belongs at the reverse-proxy layer (nginx/Caddy), not
      app code, unless this stays self-hosted-only
- [ ] If moving to Postgres: confirm the Alembic migrations are
      dialect-portable (none currently do anything SQLite-specific, but
      verify), drop the SQLite-only pragma block in `create_engine` for
      that path, load-test
- [ ] A real backup story for whichever database is chosen
- [ ] Error tracking (Sentry or similar) wired into the FastAPI exception
      handlers in `factors/entrypoints/server.py`
- [ ] Pass `version=` to `FastAPI(...)` so `/docs`'s OpenAPI schema
      reflects the actual release version (`/docs` itself is already free
      — FastAPI serves it automatically)

## Milestone 4 — Frontend production-readiness

- [ ] A test suite — there currently isn't one (Vitest + React Testing
      Library is the natural pick; Vite is already the bundler)
- [ ] A production build/serve story — `npm run build` produces static
      assets, but there's no production compose/nginx config to serve
      them alongside the API (today's `docker-compose.yml` is dev-only:
      bind mounts, `--reload`, Vite dev server)
- [ ] A real error boundary instead of per-page `(error as Error).message`
      rendering (functional today, not polished)
- [ ] Loading/empty-state pass (some pages have it, worth a consistency
      check across all of them)
- [ ] Favicon/branding pass before going public (still the Vite template
      favicon)

## Milestone 5 — Release

- [ ] Confirm the current feature set (tables/factors, generation, review
      and bulk-refine, evaluate, rules, rule overlaps) is the intended 1.0
      scope — there's no outstanding product backlog beyond what's
      shipped, so this is really just confirming "yes, this is it"
- [ ] Run a `/security-review` pass before tagging
- [ ] Bump `backend/pyproject.toml` (currently `0.1.0`) and
      `frontend/package.json` (currently `0.0.0`) to `1.0.0`
- [ ] Tag `v1.0.0`, write release notes

## Already in good shape

- Backend architecture: ports/adapters, one `XUseCases` class per feature,
  every structural decision recorded in `specs/adr/`.
- 128 backend tests, `ruff check`/`format` clean.
- `/docs` (OpenAPI) is already served automatically by FastAPI.
- Settings are already env-driven (`FACTORS_` prefix) — just needs an
  `.env.example` and production values.
- Local dev loop (Docker Compose, hot reload both sides) is solid.
