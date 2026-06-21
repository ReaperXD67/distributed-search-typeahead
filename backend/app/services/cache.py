from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.services.consistent_hash import ConsistentHashRing
from app.services.metrics import MetricsService

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    value: list[dict[str, object]] | None
    node: str | None
    hit: bool


class DistributedCache:
    def __init__(
        self,
        redis_urls: list[str],
        ttl_seconds: int,
        virtual_nodes: int,
        metrics: MetricsService,
    ) -> None:
        self.node_urls = {f"cache-{index + 1}": url for index, url in enumerate(redis_urls)}
        self.clients = {
            name: Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=0.15,
                socket_timeout=0.15,
                retry_on_timeout=False,
                health_check_interval=15,
            )
            for name, url in self.node_urls.items()
        }
        self.ring = ConsistentHashRing(list(self.clients), virtual_nodes)
        self.ttl_seconds = ttl_seconds
        self.metrics = metrics
        self._down_until: dict[str, float] = {}

    @staticmethod
    def suggestion_key(prefix: str) -> str:
        return f"suggestions:{prefix}"

    async def close(self) -> None:
        for client in self.clients.values():
            await client.aclose()

    async def get_suggestions(self, prefix: str) -> CacheResult:
        key = self.suggestion_key(prefix)
        for index, node in enumerate(self.ring.get_nodes(key)):
            if self._down_until.get(node, 0) > time.monotonic():
                continue
            try:
                raw = await self.clients[node].get(key)
                self._down_until.pop(node, None)
                if index:
                    self.metrics.increment("cache_failovers")
                if raw is not None:
                    self.metrics.increment("cache_hits")
                    return CacheResult(json.loads(raw), node, True)
                self.metrics.increment("cache_misses")
                return CacheResult(None, node, False)
            except Exception as exc:
                self._down_until[node] = time.monotonic() + 5
                logger.warning("Cache read failed on %s: %s", node, exc)
        self.metrics.increment("cache_misses")
        return CacheResult(None, None, False)

    async def set_suggestions(self, prefix: str, value: list[dict[str, object]]) -> str | None:
        key = self.suggestion_key(prefix)
        encoded = json.dumps(value, separators=(",", ":"))
        for index, node in enumerate(self.ring.get_nodes(key)):
            if self._down_until.get(node, 0) > time.monotonic():
                continue
            try:
                await self.clients[node].set(key, encoded, ex=self.ttl_seconds)
                self._down_until.pop(node, None)
                if index:
                    self.metrics.increment("cache_failovers")
                return node
            except Exception as exc:
                self._down_until[node] = time.monotonic() + 5
                logger.warning("Cache write failed on %s: %s", node, exc)
        return None

    async def invalidate_query_prefixes(self, query: str) -> int:
        deleted = 0
        for length in range(1, len(query) + 1):
            key = self.suggestion_key(query[:length])
            node = self.ring.get_node(key)
            try:
                deleted += int(await self.clients[node].delete(key))
            except Exception as exc:
                logger.warning("Cache invalidation failed on %s: %s", node, exc)
        return deleted

    async def health(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for name, client in self.clients.items():
            try:
                healthy = bool(await client.ping())
                if healthy:
                    self._down_until.pop(name, None)
                result[name] = {"healthy": healthy, "url": self.node_urls[name]}
            except Exception:
                self._down_until[name] = time.monotonic() + 5
                result[name] = {"healthy": False, "url": self.node_urls[name]}
        return result

    def explain_distribution(self, prefixes: list[str]) -> dict[str, object]:
        mappings = {prefix: self.ring.get_node(self.suggestion_key(prefix)) for prefix in prefixes}
        return {
            "algorithm": "SHA-256 consistent hash ring",
            "virtual_nodes_per_cache": self.ring.virtual_nodes,
            "nodes": list(self.ring.nodes),
            "mappings": mappings,
            "distribution": self.ring.distribution(
                [self.suggestion_key(prefix) for prefix in prefixes]
            ),
        }
