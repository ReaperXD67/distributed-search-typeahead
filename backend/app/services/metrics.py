from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import asdict, dataclass


@dataclass
class Counters:
    suggestion_requests: int = 0
    search_submissions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_failovers: int = 0
    database_reads: int = 0
    database_write_statements: int = 0
    events_flushed: int = 0
    batch_flushes: int = 0


class MetricsService:
    def __init__(self, max_latency_samples: int = 10_000) -> None:
        self.started_at = time.monotonic()
        self.counters = Counters()
        self._latencies: deque[float] = deque(maxlen=max_latency_samples)
        self.last_batch_size = 0
        self.last_flush_duration_ms = 0.0

    def increment(self, field: str, amount: int = 1) -> None:
        setattr(self.counters, field, getattr(self.counters, field) + amount)

    def observe_latency(self, milliseconds: float) -> None:
        self._latencies.append(milliseconds)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = max(0, math.ceil(percentile * len(ordered)) - 1)
        return ordered[index]

    def snapshot(self) -> dict[str, object]:
        counters = asdict(self.counters)
        cache_total = self.counters.cache_hits + self.counters.cache_misses
        write_baseline = self.counters.events_flushed
        writes = self.counters.database_write_statements
        return {
            "uptime_seconds": round(time.monotonic() - self.started_at, 1),
            **counters,
            "cache_hit_rate": round(self.counters.cache_hits / cache_total, 4)
            if cache_total
            else 0.0,
            "latency_ms": {
                "p50": round(self._percentile(list(self._latencies), 0.50), 2),
                "p95": round(self._percentile(list(self._latencies), 0.95), 2),
                "samples": len(self._latencies),
            },
            "batching": {
                "last_batch_size": self.last_batch_size,
                "last_flush_duration_ms": round(self.last_flush_duration_ms, 2),
                "naive_write_baseline": write_baseline,
                "actual_write_statements": writes,
                "write_reduction_percent": round(max(0.0, (1 - writes / write_baseline) * 100), 2)
                if write_baseline
                else 0.0,
            },
        }
