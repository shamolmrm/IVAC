import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import DEV_DATA_KEY, get_settings

log = logging.getLogger("ivac")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.is_production and settings.data_encryption_key == DEV_DATA_KEY:
        raise RuntimeError("Set DATA_ENCRYPTION_KEY: the development key must not be used.")
    docs = not settings.is_production  # API docs are not public in production
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_v1_prefix}/docs" if docs else None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if docs else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        """CSRF defence: reject state-changing requests sent from other websites."""
        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and origin not in settings.cors_origins:
                return JSONResponse({"detail": "Origin not allowed."}, status_code=403)
        return await call_next(request)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        """Log unexpected errors; never leak details to the client."""
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Something went wrong on our side."}, status_code=500)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
