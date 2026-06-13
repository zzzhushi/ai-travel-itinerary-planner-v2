"""Application configuration via pydantic-settings (env / .env).

Grows as milestones add external services; M0 needs only the log destination.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRIPPLANNER_", env_file=".env", extra="ignore")

    log_file: Path = Path("logs/app.jsonl")
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()
