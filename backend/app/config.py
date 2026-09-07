from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FACTORS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./factors.db"
    max_combinations: int = 50_000
    generation_batch_size: int = 500
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
