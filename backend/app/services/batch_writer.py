from __future__ import annotations

import asyncio
import logging
import socket
import time
import uuid

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.services.cache import DistributedCache
from app.services.metrics import MetricsService
from app.services.repository import QueryRepository

logger = logging.getLogger(__name__)


class BatchWriter:
    STREAM = "search-events"
    GROUP = "typeahead-workers"

    def __init__(
        self,
        redis: Redis,
        repository: QueryRepository,
        cache: DistributedCache,
        metrics: MetricsService,
        batch_size: int,
        flush_interval_ms: int,
    ) -> None:
        self.redis = redis
        self.repository = repository
        self.cache = cache
        self.metrics = metrics
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self.consumer = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        try:
            await self.redis.xgroup_create(self.STREAM, self.GROUP, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._task = asyncio.create_task(self._run(), name="search-count-batch-writer")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except TimeoutError:
                self._task.cancel()
        await self.flush_once(include_pending=True)

    async def enqueue(self, query: str) -> str:
        event_id = str(uuid.uuid4())
        await self.redis.xadd(
            self.STREAM,
            {"event_id": event_id, "query": query, "created_at": str(time.time())},
        )
        self.metrics.increment("search_submissions")
        return event_id

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                flushed = await self.flush_once(include_pending=True)
                if not flushed:
                    await asyncio.sleep(self.flush_interval_ms / 1000)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Batch flush failed; events remain durable in Redis Stream")
                await asyncio.sleep(1)

    async def _claim_pending(self) -> list[tuple[str, dict[str, str]]]:
        try:
            claimed = await self.redis.xautoclaim(
                self.STREAM,
                self.GROUP,
                self.consumer,
                min_idle_time=max(self.flush_interval_ms * 2, 1_000),
                start_id="0-0",
                count=self.batch_size,
            )
            return claimed[1] if len(claimed) > 1 else []
        except ResponseError:
            return []

    async def flush_once(self, include_pending: bool = False) -> int:
        messages = await self._claim_pending() if include_pending else []
        if len(messages) < self.batch_size:
            response = await self.redis.xreadgroup(
                self.GROUP,
                self.consumer,
                {self.STREAM: ">"},
                count=self.batch_size - len(messages),
                block=1,
            )
            if response:
                messages.extend(response[0][1])
        if not messages:
            return 0

        started = time.perf_counter()
        event_rows = [(fields["event_id"], fields["query"]) for _message_id, fields in messages]
        inserted_count, changed_queries = await self.repository.apply_events(event_rows)
        await self.redis.xack(self.STREAM, self.GROUP, *[message_id for message_id, _ in messages])
        for query in changed_queries:
            await self.cache.invalidate_query_prefixes(query)

        self.metrics.increment("events_flushed", inserted_count)
        self.metrics.increment("batch_flushes")
        self.metrics.last_batch_size = len(messages)
        self.metrics.last_flush_duration_ms = (time.perf_counter() - started) * 1_000
        return len(messages)
