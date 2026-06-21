from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Search Typeahead API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://typeahead:typeahead@localhost:5432/typeahead"
    redis_urls: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "redis://localhost:6379/0",
            "redis://localhost:6380/0",
            "redis://localhost:6381/0",
        ]
    )
    dataset_path: Path = Path("data/queries.csv")
    cache_ttl_seconds: int = 60
    cache_virtual_nodes: int = 128
    batch_size: int = 250
    batch_flush_interval_ms: int = 2_000
    trending_window_minutes: int = 60
    suggestion_limit: int = 10
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("redis_urls", "cors_origins", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
