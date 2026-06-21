from __future__ import annotations

import time
from collections import defaultdict

from redis.asyncio import Redis

from app.services.repository import QueryRepository


class TrendingService:
    BUCKET_SECONDS = 60

    def __init__(self, redis: Redis, repository: QueryRepository, retention_minutes: int) -> None:
        self.redis = redis
        self.repository = repository
        self.retention_minutes = retention_minutes

    @classmethod
    def bucket_key(cls, epoch_seconds: int | None = None) -> str:
        now = epoch_seconds or int(time.time())
        return f"trending:{now // cls.BUCKET_SECONDS}"

    async def record(self, query: str) -> None:
        key = self.bucket_key()
        pipe = self.redis.pipeline(transaction=False)
        pipe.zincrby(key, 1, query)
        pipe.expire(key, (self.retention_minutes + 5) * self.BUCKET_SECONDS)
        await pipe.execute()

    async def top(self, limit: int, window_minutes: int) -> tuple[list[dict[str, object]], str]:
        current_bucket = int(time.time()) // self.BUCKET_SECONDS
        keys = [f"trending:{current_bucket - offset}" for offset in range(window_minutes)]
        pipe = self.redis.pipeline(transaction=False)
        for key in keys:
            pipe.zrevrange(key, 0, 99, withscores=True)
        buckets = await pipe.execute()

        scores: defaultdict[str, float] = defaultdict(float)
        for age, entries in enumerate(buckets):
            weight = 0.5 ** (age / max(window_minutes / 4, 1))
            for query, count in entries:
                scores[query] += float(count) * weight

        if scores:
            ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
            result = [
                {"query": query, "score": round(score, 3), "rank": rank}
                for rank, (query, score) in enumerate(ranked, start=1)
            ]
            if len(result) < limit:
                live_queries = {item["query"] for item in result}
                fallback = await self.repository.top_queries(limit * 2)
                for item in fallback:
                    if item["query"] in live_queries:
                        continue
                    result.append(
                        {"query": item["query"], "score": 0.0, "rank": len(result) + 1}
                    )
                    if len(result) == limit:
                        break
            return result, "live-window"

        fallback = await self.repository.top_queries(limit)
        return [
            {"query": item["query"], "score": float(item["count"]), "rank": rank}
            for rank, item in enumerate(fallback, start=1)
        ], "popular-fallback"
