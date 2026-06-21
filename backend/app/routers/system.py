from fastapi import APIRouter, Query, Request
from sqlalchemy import text

router = APIRouter(tags=["system"])


@router.get("/metrics")
async def metrics(request: Request) -> dict[str, object]:
    snapshot = request.app.state.metrics.snapshot()
    snapshot["cache_nodes"] = await request.app.state.cache.health()
    return snapshot


@router.get("/system/cache-distribution")
async def cache_distribution(
    request: Request,
    prefixes: str = Query(default="a,app,iph,java,python,shoes,travel,music,news,ai"),
) -> dict[str, object]:
    samples = [item.strip().casefold() for item in prefixes.split(",") if item.strip()][:100]
    return request.app.state.cache.explain_distribution(samples)


@router.post("/system/flush")
async def flush_batch(request: Request) -> dict[str, object]:
    flushed = await request.app.state.batch_writer.flush_once(include_pending=True)
    return {"flushed_events": flushed, "status": "complete"}


@router.get("/health", include_in_schema=False)
async def api_health(request: Request) -> dict[str, object]:
    async with request.app.state.database.session_factory() as session:
        await session.execute(text("SELECT 1"))
    cache_nodes = await request.app.state.cache.health()
    healthy = all(node["healthy"] for node in cache_nodes.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "database": "connected",
        "cache_nodes": cache_nodes,
    }
