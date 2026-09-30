"""Cross-context FastAPI wiring: resolves the app's `Database` from
`app.state`. That's the only per-request dependency modules need now —
each module's `api/routes.py` builds its own `XUseCases(database)` from
it (cheap and stateless, so building one fresh per request costs nothing;
each use-case method opens whatever scope it needs internally, so there's
no separate unit-of-work/read-scope dependency to wire here anymore)."""

from __future__ import annotations

from fastapi import Request

from app.application.ports.database import Database


def get_database(request: Request) -> Database:
    return request.app.state.database
