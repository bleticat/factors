# factors

Decision tables generator — a QA-style combinatorial test-case tool. Define
factors and their possible values, generate the full Cartesian product as
candidate test cases, review/refine each row (possible/impossible + expected
output, with bulk edits) or save a wildcard **rule** (values for some factors,
"any" for the rest, plus an output — applied to every matching row, with the
affected-row count shown, and re-applied automatically on regeneration), then
evaluate the table by factor→value assignment.

The backend follows a layered Ports & Adapters structure — see
`backend/app/` (`domain/`, `application/`, `adapters/`, `entrypoints/`,
`composition.py`, `config.py`).

## Running locally

### Docker Compose (recommended)

```
docker compose up
```

Then open **http://localhost:5173**. This builds and runs both services:

- `backend` — FastAPI on `:8000`, runs `alembic upgrade head` on startup, then
  `uvicorn --reload`.
- `frontend` — Vite dev server on `:5173`, proxying `/api/*` to the backend
  over the compose network.

Both services bind-mount their source directory for hot reload — edit code
on the host and it picks up live. Dependencies (`.venv`, `node_modules`) live
in named Docker volumes so the container's own (Linux) install is used
instead of whatever's on the host; add a new dependency and rebuild with
`docker compose up --build`.

The SQLite database lives at `backend/factors.db` on the host (via the bind
mount), so data persists across `docker compose down`/`up`. Delete that file
to reset.

### Without Docker

Two terminals:

```
cd backend && uv run alembic upgrade head && uv run uvicorn app.entrypoints.server:app --reload
cd frontend && npm run dev
```

Then open the printed Vite URL (default `http://localhost:5173`).
