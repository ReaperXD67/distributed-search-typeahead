from app.services.metrics import MetricsService


def test_metrics_report_cache_rate_and_write_reduction() -> None:
    metrics = MetricsService()
    metrics.increment("cache_hits", 3)
    metrics.increment("cache_misses")
    metrics.increment("events_flushed", 100)
    metrics.increment("database_write_statements", 2)
    for duration in range(1, 101):
        metrics.observe_latency(float(duration))

    snapshot = metrics.snapshot()
    assert snapshot["cache_hit_rate"] == 0.75
    assert snapshot["latency_ms"]["p95"] == 95.0
    assert snapshot["batching"]["write_reduction_percent"] == 98.0
