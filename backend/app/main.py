from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.combinations.api.routes import router as combinations_router
from app.config import settings
from app.generation.api.routes import router as generation_router
from app.generation.startup_sweep import sweep_stale_generation_jobs
from app.rules.api.routes import router as rules_router
from app.shared.adapters.sqlalchemy_database import SqlAlchemyDatabase, create_engine
from app.shared.errors import NotFoundError, ValidationError
from app.tables.api.routes import router as tables_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(settings.database_url)
    database = SqlAlchemyDatabase(engine)
    app.state.database = database

    swept = await sweep_stale_generation_jobs(database)
    if swept:
        logger.warning(
            "Swept %d stale 'running' generation job(s) to 'failed' on startup", swept
        )

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
    async def handle_validation(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    # `tables`, `rules`, `combinations`, and `generation` each contribute a
    # disjoint set of paths under the same `/api/decision-tables` prefix —
    # they're sub-modules of the one bounded context this service has, not
    # separate API surfaces.
    for router in (tables_router, rules_router, combinations_router, generation_router):
        app.include_router(
            router, prefix="/api/decision-tables", tags=["decision-tables"]
        )

    return app


app = create_app()
