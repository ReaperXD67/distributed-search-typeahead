import asyncio
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request, status

from app.schemas import (
    SearchRequest,
    SearchResponse,
    SuggestionsResponse,
    TrendingResponse,
    normalize_query,
)

router = APIRouter(tags=["search"])


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=10),
) -> SuggestionsResponse:
    started = time.perf_counter()
    prefix = normalize_query(q)
    request.app.state.metrics.increment("suggestion_requests")
    cached = await request.app.state.cache.get_suggestions(prefix)
    if cached.hit and cached.value is not None:
        items = cached.value[:limit]
        node = cached.node
    else:
        items = await request.app.state.repository.suggestions(
            prefix, request.app.state.settings.suggestion_limit
        )
        node = await request.app.state.cache.set_suggestions(prefix, items)
    return SuggestionsResponse(
        query=prefix,
        suggestions=items[:limit],
        cached=cached.hit,
        cache_node=node,
        duration_ms=round((time.perf_counter() - started) * 1_000, 2),
    )


@router.post("/search", response_model=SearchResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_search(payload: SearchRequest, request: Request) -> SearchResponse:
    event_id, _ = await asyncio.gather(
        request.app.state.batch_writer.enqueue(payload.query),
        request.app.state.trending.record(payload.query),
    )
    return SearchResponse(
        query=payload.query,
        event_id=event_id,
        message=f'Searched for "{payload.query}". Popularity update queued.',
    )


@router.get("/trending", response_model=TrendingResponse)
async def trending(
    request: Request,
    limit: int = Query(default=10, ge=1, le=20),
    window_minutes: int = Query(default=60, ge=5, le=1_440),
) -> TrendingResponse:
    searches, source = await request.app.state.trending.top(limit, window_minutes)
    return TrendingResponse(
        window_minutes=window_minutes,
        generated_at=datetime.now(UTC),
        source=source,
        searches=searches,
    )
