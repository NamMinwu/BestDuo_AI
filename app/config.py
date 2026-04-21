from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="local")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    database_url: str
    database_pool_min: int = Field(default=1)
    database_pool_max: int = Field(default=5)
    database_query_timeout_ms: int = Field(default=1500)

    redis_url: str
    redis_cache_ttl_seconds: int = Field(default=3600)

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="exaone3.5:2.4b-instruct-q4_K_M")
    ollama_timeout_ms: int = Field(default=15000)
    ollama_num_predict: int = Field(default=256)
    ollama_temperature: float = Field(default=0.2)

    internal_api_key: str = Field(default="")

    sentry_dsn: str = Field(default="")
    sentry_environment: str = Field(default="local")
    sentry_release: str = Field(default="bestduo-ai@local")
    prometheus_enabled: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
