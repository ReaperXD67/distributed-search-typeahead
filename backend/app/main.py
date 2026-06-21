from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import Database
from app.routers import search, system
from app.services.batch_writer import BatchWriter
from app.services.cache import DistributedCache
from app.services.metrics import MetricsService
from app.services.repository import QueryRepository
from app.services.trending import TrendingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    metrics = MetricsService()
    database = Database(settings)
    await database.connect()
    dataset_size = await database.seed_if_empty(settings.dataset_path)
    logger.info("Dataset ready with %s queries", dataset_size)

    repository = QueryRepository(database.session_factory, metrics)
    cache = DistributedCache(
        settings.redis_urls,
        settings.cache_ttl_seconds,
        settings.cache_virtual_nodes,
        metrics,
    )
    event_redis = cache.clients["cache-1"]
    trending_service = TrendingService(event_redis, repository, settings.trending_window_minutes)
    batch_writer = BatchWriter(
        event_redis,
        repository,
        cache,
        metrics,
        settings.batch_size,
        settings.batch_flush_interval_ms,
    )
    await batch_writer.start()

    app.state.settings = settings
    app.state.metrics = metrics
    app.state.database = database
    app.state.repository = repository
    app.state.cache = cache
    app.state.trending = trending_service
    app.state.batch_writer = batch_writer
    yield

    await batch_writer.stop()
    await cache.close()
    await database.close()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Low-latency typeahead with consistent-hash distributed caching, "
        "windowed trending searches, and durable batch writes."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error request_id=%s", request_id)
        response = JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred", "request_id": request_id},
        )
    duration_ms = (time.perf_counter() - started) * 1_000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    if hasattr(request.app.state, "metrics") and request.url.path.endswith("/suggestions"):
        request.app.state.metrics.observe_latency(duration_ms)
    return response


app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(system.router, prefix=settings.api_prefix)


@app.get("/health", include_in_schema=False)
async def health(request: Request) -> dict[str, object]:
    return await system.api_health(request)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}
