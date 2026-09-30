"""ASGI entrypoint. `uvicorn app.entrypoints.server:app` starts the HTTP server."""

from __future__ import annotations

from app.composition import create_app

app = create_app()
