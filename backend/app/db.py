import asyncio
import csv
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings

logger = logging.getLogger(__name__)


def _read_dataset(dataset_path: Path) -> list[tuple[str, str, int]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    records: list[tuple[str, str, int]] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            query = row["query"].strip()
            records.append((query, query.casefold(), int(row["count"])))
    return records


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def connect(self, attempts: int = 20) -> None:
        from app import models  # noqa: F401

        for attempt in range(1, attempts + 1):
            try:
                async with self.engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                return
            except Exception:
                if attempt == attempts:
                    raise
                await asyncio.sleep(min(attempt * 0.5, 3))

    async def close(self) -> None:
        await self.engine.dispose()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def seed_if_empty(self, dataset_path: Path) -> int:
        from app.models import SearchQuery

        async with self.session_factory() as session:
            existing = await session.scalar(select(func.count()).select_from(SearchQuery))
        if existing:
            return int(existing)
        records = await asyncio.to_thread(_read_dataset, dataset_path)

        raw_url = self.settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        connection = await asyncpg.connect(raw_url)
        try:
            await connection.copy_records_to_table(
                "search_queries",
                records=records,
                columns=["query", "normalized_query", "count"],
            )
        finally:
            await connection.close()
        logger.info("Seeded %s search queries", len(records))
        return len(records)
