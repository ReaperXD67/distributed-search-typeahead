from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import ProcessedSearchEvent, SearchQuery
from app.services.metrics import MetricsService


class QueryRepository:
    def __init__(self, sessions: async_sessionmaker, metrics: MetricsService) -> None:
        self.sessions = sessions
        self.metrics = metrics

    async def suggestions(self, prefix: str, limit: int = 10) -> list[dict[str, object]]:
        escaped_prefix = (
            prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        async with self.sessions() as session:
            rows = await session.execute(
                select(SearchQuery.query, SearchQuery.count)
                .where(SearchQuery.normalized_query.like(f"{escaped_prefix}%", escape="\\"))
                .order_by(SearchQuery.count.desc(), SearchQuery.query.asc())
                .limit(limit)
            )
        self.metrics.increment("database_reads")
        return [{"query": query, "count": count} for query, count in rows.all()]

    async def top_queries(self, limit: int = 10) -> list[dict[str, object]]:
        async with self.sessions() as session:
            rows = await session.execute(
                select(SearchQuery.query, SearchQuery.count)
                .order_by(SearchQuery.count.desc(), SearchQuery.query.asc())
                .limit(limit)
            )
        self.metrics.increment("database_reads")
        return [{"query": query, "count": count} for query, count in rows.all()]

    async def apply_events(self, events: list[tuple[str, str]]) -> tuple[int, list[str]]:
        """Persist a stream batch exactly once and return inserted event count + queries."""
        if not events:
            return 0, []
        values = [{"event_id": uuid.UUID(event_id), "query": query} for event_id, query in events]
        async with self.sessions() as session, session.begin():
            event_statement = (
                insert(ProcessedSearchEvent)
                .values(values)
                .on_conflict_do_nothing(index_elements=[ProcessedSearchEvent.event_id])
                .returning(ProcessedSearchEvent.query)
            )
            inserted = list((await session.scalars(event_statement)).all())
            self.metrics.increment("database_write_statements")
            if inserted:
                aggregates = Counter(inserted)
                query_values = [
                    {"query": query, "normalized_query": query.casefold(), "count": increment}
                    for query, increment in aggregates.items()
                ]
                query_statement = insert(SearchQuery).values(query_values)
                query_statement = query_statement.on_conflict_do_update(
                    index_elements=[SearchQuery.query],
                    set_={
                        "count": SearchQuery.count + query_statement.excluded.count,
                        "normalized_query": query_statement.excluded.normalized_query,
                        "updated_at": func.now(),
                    },
                )
                await session.execute(query_statement)
                self.metrics.increment("database_write_statements")
        return len(inserted), list(dict.fromkeys(inserted))
