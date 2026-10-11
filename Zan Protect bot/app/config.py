from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", hide_input_in_errors=True)
    openai_api_key: str = ""
    openai_model: str = "gpt-6-sol"
    reasoning_effort: str = "medium"
    telegram_bot_token: str = ""
    database_url: str = "postgresql://zan:change-local-password@localhost:5432/zan"
    api_secret: str = Field(min_length=32)
    session_secret: str = Field(min_length=32)
    enable_web_search: bool = False
    consultation_url: str = ""
    admin_secret: str = ""
    data_encryption_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=512, ge=256, le=1536)
    enable_semantic_search: bool = True
    verify_answers: bool = True
    daily_request_limit: int = Field(default=30, ge=1, le=500)
    max_concurrent_requests: int = Field(default=4, ge=1, le=16)
    max_queue_jobs: int = Field(default=200, ge=1, le=2000)
    font_path: str = ""
    session_ttl_seconds: int = Field(default=1800, ge=60, le=1800)
    max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=10 * 1024 * 1024)
    max_input_chars: int = Field(default=24000, ge=1000, le=24000)

    def validate_bot(self) -> None:
        required = ("telegram_bot_token", "openai_api_key", "data_encryption_key")
        missing = [name.upper() for name in required if not getattr(self, name).strip()]
        if missing:
            raise ValueError("Missing bot settings: " + ", ".join(missing) + ". Set them in Railway Variables.")
        try:
            Fernet(self.data_encryption_key.encode())
        except (ValueError, TypeError):
            raise ValueError("DATA_ENCRYPTION_KEY must be a valid Fernet key. See docs/RAILWAY.md.") from None


@lru_cache
def settings() -> Settings:
    return Settings()
