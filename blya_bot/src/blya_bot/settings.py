"""Application settings using pydantic-settings for lazy loading."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseModel):
    """Telegram bot settings."""

    bot_token: str
    transcribe_command: str = "/t"
    use_webhook: bool = False
    webhook_url: str | None = None
    webhook_path: str = "/webhook"

    @model_validator(mode="after")
    def validate_webhook(self) -> "TelegramSettings":
        """Validate webhook settings."""
        if self.use_webhook:
            if self.webhook_url is None:
                raise ValueError("telegram.webhook_url must be set when telegram.use_webhook is True")
            if not self.webhook_path.startswith("/"):
                raise ValueError("telegram.webhook_path must begin with '/'")
        return self


class ServiceSettings(BaseModel):
    """Service-level settings."""

    my_nerves_limit: int = 5 * 60
    polite_response: str = "Бот сломан, больше пяти минут войса ему не переварить"
    ignore_forwarded: bool = True
    log_level: str = "info"
    log_colors: bool = False
    dict_file: Path = Path("./fixtures/dict.bb")


class RecognitionSettings(BaseModel):
    """Speech recognition settings."""

    engine: Literal["vosk", "pywhispercpp", "faster-whisper"]
    engine_options: dict[str, Any] = {}

    @field_validator("engine", mode="before")
    @classmethod
    def lowercase_engine(cls, v: str) -> str:
        """Normalize engine name to lowercase."""
        return v.lower() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_engine_options(self) -> "RecognitionSettings":
        """Validate engine-specific options."""
        if self.engine == "vosk" and self.engine_options.get("model_path") is None:
            raise ValueError("recognition.engine_options must contain 'model_path' for vosk engine")
        if self.engine in ("pywhispercpp", "faster-whisper") and self.engine_options.get("model") is None:
            raise ValueError(f"recognition.engine_options must contain 'model' for {self.engine}")
        return self


class HealthCheckSettings(BaseModel):
    """Health check server settings."""

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8080
    path: str = "/health/live"


class CacheSettings(BaseModel):
    """Cache settings."""

    engine: Literal["sqlite", "memory"] | None = None
    params: dict[str, Any] = {}
    periodic_cleanup: int | None = None

    @model_validator(mode="after")
    def set_defaults(self) -> "CacheSettings":
        """Set default parameters based on engine."""
        if self.engine == "sqlite" and self.params.get("db_path") is None:
            self.params["db_path"] = "transcription_cache.db"
        elif self.engine == "memory" and self.params.get("ttl") is None:
            self.params["ttl"] = 60 * 60
        return self


class Settings(BaseSettings):
    """Application settings with nested structure.

    Environment variables use double underscore as delimiter:
      TELEGRAM__BOT_TOKEN=xxx
      SERVICE__LOG_LEVEL=debug
      RECOGNITION__ENGINE=faster-whisper
      RECOGNITION__ENGINE_OPTIONS={"model": "small"}
    """

    telegram: TelegramSettings
    service: ServiceSettings = ServiceSettings()
    recognition: RecognitionSettings
    health_check: HealthCheckSettings = HealthCheckSettings()
    cache: CacheSettings = CacheSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()  # type: ignore[call-arg]
