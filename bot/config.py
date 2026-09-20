"""Central configuration. Everything comes from env — nothing hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    bot_token: str = field(default_factory=lambda: _env("BOT_TOKEN"))
    owner_id: int = field(default_factory=lambda: _env_int("OWNER_ID", 0))

    ai_backend: str = field(default_factory=lambda: _env("AI_BACKEND", "bridge"))
    opencode_serve_url: str = field(
        default_factory=lambda: _env("OPENCODE_SERVE_URL", "http://127.0.0.1:4096")
    )
    opencode_model: str = field(
        default_factory=lambda: _env("OPENCODE_MODEL", "opencode/muse-spark-1.3")
    )
    opencode_fallback_model: str = field(
        default_factory=lambda: _env("OPENCODE_FALLBACK_MODEL", "opencode/mimo-v2.5-free")
    )

    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_base_url: str = field(
        default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini"))

    data_dir: str = field(default_factory=lambda: _env("DATA_DIR", "./data"))
    mode: str = field(default_factory=lambda: _env("MODE", "polling"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8080))
    webhook_url: str = field(default_factory=lambda: _env("WEBHOOK_URL"))

    dashboard_user: str = field(default_factory=lambda: _env("DASHBOARD_USER", "admin"))
    dashboard_pass: str = field(default_factory=lambda: _env("DASHBOARD_PASS", "changeme"))

    timezone: str = field(default_factory=lambda: _env("TZ", "Asia/Tehran"))

    # Prompt UX (from spec)
    chunk_size: int = 200
    history_limit: int = 30

    @property
    def db_path(self) -> str:
        """SQLite database path. Always inside DATA_DIR (Railway volume)."""
        return os.path.join(self.data_dir, "bot_data.db")

    def validate(self) -> None:
        """Raise RuntimeError if required settings are missing."""
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not set")
        if not self.owner_id:
            raise RuntimeError("OWNER_ID is not set")

    def is_owner(self, user_id: int) -> bool:
        """Check whether a Telegram user is the bot owner."""
        return user_id == self.owner_id


CONFIG = Config()
