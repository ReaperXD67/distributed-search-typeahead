from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def normalize_query(value: str) -> str:
    return " ".join(value.strip().casefold().split())


class Suggestion(BaseModel):
    query: str
    count: int


class SuggestionsResponse(BaseModel):
    query: str
    suggestions: list[Suggestion]
    cached: bool
    cache_node: str | None
    duration_ms: float


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = normalize_query(value)
        if not cleaned:
            raise ValueError("query cannot be blank")
        return cleaned


class SearchResponse(BaseModel):
    status: str = "searched"
    query: str
    event_id: str
    queued: bool = True
    message: str


class TrendingItem(BaseModel):
    query: str
    score: float
    rank: int


class TrendingResponse(BaseModel):
    window_minutes: int
    generated_at: datetime
    source: str
    searches: list[TrendingItem]
