"""
bot/config.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — SD-05 Simplified Configuration
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import FrozenSet

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    bot_token: str = Field(..., description="Telegram BotFather token")
    admin_user_ids: str = Field(
        "", description="Comma-separated Telegram user IDs with admin rights"
    )

    # ── Groq / LLM (used for slot extraction only) ───────────────────────────
    groq_api_key: str = Field(..., description="Groq cloud API key")
    groq_model: str = Field(
        "llama-3.3-70b-versatile", description="Groq model identifier"
    )

    # ── Database ──────────────────────────────────────────────────────────────
    db_path: Path = Field(Path("./data/mugen.db"))

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field("INFO")

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def _coerce_admins(cls, v: object) -> str:
        return str(v) if v is not None else ""

    @property
    def admin_ids(self) -> FrozenSet[int]:
        if not self.admin_user_ids.strip():
            return frozenset()
        return frozenset(
            int(uid.strip())
            for uid in self.admin_user_ids.split(",")
            if uid.strip().isdigit()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
