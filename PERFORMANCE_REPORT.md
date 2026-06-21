# Performance and Reliability Report

Measured on 22 June 2026 using the production Docker Compose stack on Docker Desktop for Windows. The dataset contained 100,000 query rows. All figures are reproducible with `backend/scripts/benchmark.py` and the metrics endpoint.

## Suggestion latency

| Measurement | Requests | Concurrency | Mean | p95 | Failures |
|---|---:|---:|---:|---:|---:|
| Server-side API instrumentation | 5,001 | mixed, up to 50 | — | **18.86 ms** | 0 |
| Client inside Docker network | 2,000 | 50 | 117.85 ms | 171.77 ms | 0 |
| Windows host through Docker NAT | 1,000 | 10 | 55.80 ms | 123.42 ms | 0 |

The server-side metric surrounds FastAPI request processing and is the best signal for service performance. Client figures include HTTP connection scheduling, Python client work, and Docker Desktop/WSL networking. The cache hit rate after the 5,001-request mixed-prefix run was **98.1%**; server-side p50 was **2.27 ms**.

## Batch-write reduction

A burst sent 500 identical searches for `distributed systems course`.

| Signal | Result |
|---|---:|
| Accepted submissions | 500 / 500 |
| Persisted count increase | 500 |
| Total events in measured worker window | 501 |
| Batch flushes | 4 |
| PostgreSQL write statements | 8 |
| Naive synchronous-write baseline | 501 |
| Write reduction | **98.4%** |

Each flush uses two write statements regardless of repeated-event volume: one bulk idempotency insert and one bulk aggregated query upsert. This is why repeated queries collapse especially well.

## Consistent-hash distribution and failover

The ring uses SHA-256 and 128 virtual nodes per physical cache. A 10,000-key unit test verifies that each of three nodes receives a reasonable share. Adding a fourth node moves roughly one quarter of keys rather than invalidating the whole cache.

Failure drill:

1. Map `premium` to `cache-2` using `/api/v1/system/cache-distribution`.
2. Stop only `redis-b`.
3. Request ten suggestions for `premium`.
4. Observe the health endpoint report `degraded` while `cache-1` serves the request.
5. Restart `redis-b` and observe health recovery.

Measured degraded-path response: **178 ms**, ten suggestions returned, and two failover operations recorded (read plus write). Redis socket timeouts are 150 ms and a five-second failure circuit prevents every request from repeatedly waiting on the dead node.

## Test evidence

- Backend: 8 unit tests passed.
- Frontend: 2 unit tests passed.
- Backend lint: Ruff clean.
- Frontend: strict TypeScript and Vite production build clean.
- Dataset: 100,000 database rows verified after clean-volume bootstrap.
- Browser: search, ten-result dropdown, Arrow navigation, Enter submission, loading/queued states, desktop and 390 px responsive layout verified.
- Containers: PostgreSQL, three Redis nodes, backend, and frontend all passed health checks.

## Interpretation

The cache path meets the assignment goal: most service work completes well below a frame budget, and the database is bypassed on 98% of repeated prefix requests. The batching path reduces write statements by more than 98% for a bursty repeated-query workload. Under a cache-node failure, the API remains available and explicitly exposes degraded health instead of hiding the incident.

