"""Exercise the production stack through its public HTTP contracts."""

from __future__ import annotations

import asyncio

import httpx


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10) as client:
        health = (await client.get("/health")).json()
        assert health["status"] == "healthy"

        first = (await client.get("/api/v1/suggestions", params={"q": "iph"})).json()
        second = (await client.get("/api/v1/suggestions", params={"q": "iph"})).json()
        assert len(first["suggestions"]) == 10
        assert first["suggestions"] == sorted(
            first["suggestions"], key=lambda item: (-item["count"], item["query"])
        )
        assert second["cached"] is True

        search = await client.post(
            "/api/v1/search", json={"query": "production smoke test query"}
        )
        assert search.status_code == 202
        assert search.json()["status"] == "searched"

        trending = (await client.get("/api/v1/trending", params={"limit": 10})).json()
        assert any(item["query"] == "production smoke test query" for item in trending["searches"])

        distribution = (await client.get("/api/v1/system/cache-distribution")).json()
        assert len(distribution["nodes"]) == 3

    print("Production smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())

