"""FastAPI application entrypoint for the C2C backend."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.common.exceptions import AppError, register_app_error_handler
from app.config import get_settings

settings = get_settings()
start_time = time.monotonic()



def create_app() -> FastAPI:
    """Application factory used by tests and production."""

    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["meta"], response_class=RedirectResponse)
    def index() -> RedirectResponse:  # pragma: no cover - trivial redirect
        """Redirect root path to Swagger documentation."""

        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["meta"], summary="Health check")
    def health() -> dict[str, object]:
        """Simple liveliness probe reporting uptime and environment."""

        uptime_seconds = time.monotonic() - start_time
        return {
            "ok": True,
            "env": settings.app_env,
            "uptime": round(uptime_seconds, 2),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    from app.routers import (  # pylint: disable=import-outside-toplevel
        admin,
        audit,
        auth,
        deals,
        health as health_router,
        membership,
        products,
        promotions,
    )

    app.include_router(health_router.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(deals.router, prefix="/api")
    app.include_router(promotions.router, prefix="/api")
    app.include_router(membership.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")

    register_app_error_handler(app)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "message": "Validation failed"},
        )

    return app


app = create_app()

