"""Data Governance API main application."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .container import AppContainer
from .registry_connections.interface.router import router as registry_connection_router
from .schema.interface.router import router as schema_router
from .schema.interface.routers.policy_router import router as schema_policy_router
from .shared.error_handlers import format_validation_error
from .shared.logging_config import configure_structlog, get_logger
from .shared.middleware import RequestLoggingMiddleware
from .shared.settings import settings

configure_structlog()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    container = app.state.container  # type: ignore[attr-defined]

    try:
        container.init_resources()

        logger.info("app_startup_completed", environment=settings.environment)
        yield
    except Exception as e:
        logger.error(
            "app_startup_failed",
            error_type=e.__class__.__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
    finally:
        container.shutdown_resources()
        logger.info("app_shutdown_completed")


def create_app() -> FastAPI:
    docs_url = None if settings.is_production else "/swagger"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        default_response_class=ORJSONResponse,
        title="Data Governance API",
        description="Schema Registry connections and schema governance API",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        swagger_ui_oauth2_redirect_url=None
        if settings.is_production
        else "/swagger/oauth2-redirect",
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "defaultModelRendering": "example",
            "displayRequestDuration": True,
            "docExpansion": "none",
            "syntaxHighlight.theme": "obsidian",
            "persistAuthorization": True,
        },
    )

    cors_origins = settings.parsed_cors_origins
    logger.info(
        "cors_configured",
        origins=cors_origins,
        environment=settings.environment,
    )

    app.add_middleware(RequestLoggingMiddleware)  # type: ignore[arg-type]
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    container = AppContainer()
    app.state.container = container
    app.state.infrastructure_container = container.infrastructure_container()
    app.state.registry_container = container.registry_container()
    app.state.schema_container = container.schema_container()

    container.wire(
        packages=[
            "app.registry_connections.interface",
            "app.schema.interface",
            "app.schema.interface.routers",
        ]
    )

    app.include_router(registry_connection_router, prefix="/api")
    app.include_router(schema_router, prefix="/api")
    app.include_router(schema_policy_router, prefix="/api")

    @app.get("/api")
    @app.get("/api/")
    @app.get("/api/v1")
    @app.get("/api/v1/")
    async def api_info() -> dict[str, str]:
        return {"message": "Data Governance API", "version": "1.0.0"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(
            "validation_error",
            error_count=len(exc.errors()),
            errors=exc.errors(),
        )
        friendly_message = format_validation_error(exc)  # type: ignore[arg-type]
        return ORJSONResponse(status_code=422, content={"detail": friendly_message})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code >= 500:
            logger.error(
                "internal_server_error",
                status_code=exc.status_code,
                detail=str(exc.detail),
                exc_info=True,
            )
            return ORJSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": "An unexpected server error occurred. Please contact the administrator."
                },
            )
        return ORJSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            error_type=exc.__class__.__name__,
            error_message=str(exc),
            exc_info=True,
        )
        return ORJSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. The technical details have been logged."
            },
        )

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        return ORJSONResponse(status_code=404, content={"detail": "Resource not found"})

    return app


app = create_app()
