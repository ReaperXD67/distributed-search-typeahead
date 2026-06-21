import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"
    __table_args__ = (
        Index(
            "ix_search_queries_normalized_pattern",
            "normalized_query",
            postgresql_ops={"normalized_query": "text_pattern_ops"},
        ),
        Index("ix_search_queries_count", "count"),
    )

    query: Mapped[str] = mapped_column(Text, primary_key=True)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProcessedSearchEvent(Base):
    __tablename__ = "processed_search_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    query: Mapped[str] = mapped_column(String(512), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
