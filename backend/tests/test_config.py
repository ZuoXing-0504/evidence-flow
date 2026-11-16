import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings_use_offline_search() -> None:
    settings = Settings(_env_file=None)

    assert settings.web_search_provider == "mock"
    assert settings.llm_provider == "mock"
    assert settings.embedding_provider == "mock"
    assert settings.vector_store_provider == "memory"
    assert settings.max_research_iterations == 2


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings(app_cors_origins=["*"], _env_file=None)


def test_bocha_provider_requires_key() -> None:
    settings = Settings(web_search_provider="bocha", bocha_api_key="", _env_file=None)

    with pytest.raises(ValueError, match="BOCHA_API_KEY"):
        settings.validate_runtime()


def test_dashscope_provider_requires_key() -> None:
    settings = Settings(llm_provider="dashscope", dashscope_api_key="", _env_file=None)

    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        settings.validate_runtime()


def test_dashscope_embeddings_require_key() -> None:
    settings = Settings(embedding_provider="dashscope", dashscope_api_key="", _env_file=None)

    with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
        settings.validate_runtime()


def test_milvus_collection_prefix_is_validated() -> None:
    with pytest.raises(ValidationError, match="MILVUS_COLLECTION_PREFIX"):
        Settings(milvus_collection_prefix="invalid-prefix", _env_file=None)


def test_production_requires_strong_secret() -> None:
    settings = Settings(app_env="production", app_secret_key="short", _env_file=None)

    with pytest.raises(ValueError, match="at least 32"):
        settings.validate_runtime()
