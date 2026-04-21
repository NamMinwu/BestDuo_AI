from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import asyncpg
import httpx
from redis.asyncio import Redis, from_url

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Clients:
    db: asyncpg.Pool | None
    redis: Redis | None
    ollama: httpx.AsyncClient
    settings: Settings


async def build_clients(settings: Settings) -> Clients:
    db = await _init_db_pool(settings)
    redis = await _init_redis(settings)
    ollama = httpx.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=httpx.Timeout(settings.ollama_timeout_ms / 1000.0),
    )
    return Clients(db=db, redis=redis, ollama=ollama, settings=settings)


async def close_clients(clients: Clients) -> None:
    await clients.ollama.aclose()
    if clients.redis is not None:
        await clients.redis.aclose()
    if clients.db is not None:
        await clients.db.close()


async def _init_db_pool(settings: Settings) -> asyncpg.Pool | None:
    try:
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.database_pool_min,
            max_size=settings.database_pool_max,
            command_timeout=settings.database_query_timeout_ms / 1000.0,
            server_settings={"default_transaction_read_only": "on"},
        )
        return pool
    except (OSError, asyncpg.PostgresError) as exc:
        logger.warning("database pool init failed, running degraded: %s", exc)
        return None


async def _init_redis(settings: Settings) -> Redis | None:
    try:
        client: Redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await client.ping()
        return client
    except Exception as exc:  # noqa: BLE001 — redis client raises broad ConnectionError
        logger.warning("redis init failed, running degraded: %s", exc)
        return None


async def probe_ollama(clients: Clients) -> dict[str, Any]:
    try:
        resp = await clients.ollama.get("/api/tags")
        resp.raise_for_status()
        models = [m.get("name") for m in resp.json().get("models", [])]
        configured = clients.settings.ollama_model
        return {
            "status": "up",
            "configured_model": configured,
            "model_loaded": configured in models,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


async def probe_db(clients: Clients) -> dict[str, Any]:
    if clients.db is None:
        return {"status": "down", "error": "pool not initialized"}
    try:
        async with clients.db.acquire() as conn:
            value = await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=1.0)
        return {"status": "up" if value == 1 else "degraded"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


async def probe_redis(clients: Clients) -> dict[str, Any]:
    if clients.redis is None:
        return {"status": "down", "error": "client not initialized"}
    try:
        pong = await clients.redis.ping()
        return {"status": "up" if pong else "degraded"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}
