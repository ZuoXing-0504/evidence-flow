from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "EvidenceFlow"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: SecretStr = SecretStr("development-only-change-me-please")
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = (
        "postgresql+asyncpg://evidence_flow:evidence_flow@localhost:5432/evidence_flow"
    )
    redis_url: str = "redis://localhost:6379/0"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "evidence_flow"

    dashscope_api_key: SecretStr = SecretStr("")
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_reasoning_model: str = "qwen-plus"
    llm_fast_model: str = "qwen-turbo"
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = 1024

    bocha_api_key: SecretStr = SecretStr("")
    bocha_base_url: str = "https://api.bochaai.com/v1"
    web_search_provider: Literal["bocha", "mock"] = "mock"
    max_research_iterations: int = Field(default=2, ge=0, le=5)

    @field_validator("app_cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard CORS origins are not allowed")
        return value

    @field_validator("app_secret_key")
    @classmethod
    def require_production_secret(cls, value: SecretStr, info: object) -> SecretStr:
        # Production validation is completed in validate_runtime because field order is not stable.
        return value

    def validate_runtime(self) -> None:
        if self.app_env == "production" and len(self.app_secret_key.get_secret_value()) < 32:
            raise ValueError("APP_SECRET_KEY must contain at least 32 characters in production")
        if self.web_search_provider == "bocha" and not self.bocha_api_key.get_secret_value():
            raise ValueError("BOCHA_API_KEY is required when WEB_SEARCH_PROVIDER=bocha")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
