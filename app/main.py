from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client import multiprocess as prom_multiprocess

from app.clients import Clients, build_clients, close_clients, probe_db, probe_ollama, probe_redis
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _configure_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    _configure_sentry(settings)

    clients = await build_clients(settings)
    app.state.clients = clients
    logger.info("bestduo_AI started in env=%s", settings.app_env)
    try:
        yield
    finally:
        await close_clients(clients)
        logger.info("bestduo_AI stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="BestDuo AI — NLP Duo Coach",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["ops"])
    async def health(request: Request) -> dict[str, Any]:
        clients: Clients = request.app.state.clients
        db = await probe_db(clients)
        redis = await probe_redis(clients)
        ollama = await probe_ollama(clients)
        overall = "up" if all(p["status"] == "up" for p in (db, redis, ollama)) else "degraded"
        return {
            "status": overall,
            "checks": {"db": db, "redis": redis, "ollama": ollama},
        }

    @app.get("/metrics", tags=["ops"])
    async def metrics() -> Response:
        settings = get_settings()
        if not settings.prometheus_enabled:
            return Response(status_code=404)
        registry = CollectorRegistry()
        try:
            prom_multiprocess.MultiProcessCollector(registry)
        except (ValueError, KeyError):
            from prometheus_client import REGISTRY

            registry = REGISTRY
        return Response(
            content=generate_latest(registry),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


app = create_app()
