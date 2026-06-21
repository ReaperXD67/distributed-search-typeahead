from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx

PREFIXES = ["i", "ip", "iph", "iphone", "py", "python", "best", "wire", "java", "run"]


async def main(base_url: str, requests: int, concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    failures = 0

    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:

        async def hit(index: int) -> None:
            nonlocal failures
            async with semaphore:
                started = time.perf_counter()
                response = await client.get(
                    "/api/v1/suggestions", params={"q": PREFIXES[index % len(PREFIXES)]}
                )
                latencies.append((time.perf_counter() - started) * 1_000)
                if response.status_code != 200:
                    failures += 1

        await asyncio.gather(*(hit(index) for index in range(requests)))

    ordered = sorted(latencies)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print(f"requests={requests} concurrency={concurrency} failures={failures}")
    print(f"mean_ms={statistics.mean(latencies):.2f} p95_ms={p95:.2f} max_ms={max(latencies):.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=1_000)
    parser.add_argument("--concurrency", type=int, default=40)
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.requests, args.concurrency))
