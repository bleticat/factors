"""Cross-context FastAPI wiring shared by every module's `api/routes.py`."""

from __future__ import annotations

from fastapi import Request

from app.shared.mediator.mediator import Mediator


def get_mediator(request: Request) -> Mediator:
    return request.app.state.mediator
