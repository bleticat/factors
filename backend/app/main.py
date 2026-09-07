from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.composition import build_mediator
from app.config import settings
from app.decision_tables.api.router import router as decision_tables_router
from app.decision_tables.lifecycle.startup_sweep import sweep_stale_generation_jobs
from app.shared.database.sqlalchemy_database import SqlAlchemyDatabase, create_engine
from app.shared.errors import NotFoundError, UnregisteredRequestError, ValidationError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(settings.database_url)
    database = SqlAlchemyDatabase(engine)
    mediator = build_mediator(database, max_combinations=settings.max_combinations)
    app.state.mediator = mediator

    swept = await sweep_stale_generation_jobs(mediator)
    if swept:
        logger.warning("Swept %d stale 'running' generation job(s) to 'failed' on startup", swept)

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Factors — Decision Table Generator", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def handle_validation(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(UnregisteredRequestError)
    async def handle_unregistered(_request: Request, exc: UnregisteredRequestError) -> JSONResponse:
        logger.error("Unregistered mediator request: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(
        decision_tables_router, prefix="/api/decision-tables", tags=["decision-tables"]
    )

    return app


app = create_app()
