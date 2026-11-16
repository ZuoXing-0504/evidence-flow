from collections.abc import Iterator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolate_external_provider_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for variable in (
        "BOCHA_API_KEY",
        "DASHSCOPE_API_KEY",
        "WEB_SEARCH_PROVIDER",
        "LLM_PROVIDER",
        "EMBEDDING_PROVIDER",
        "VECTOR_STORE_PROVIDER",
        "MAX_RESEARCH_ITERATIONS",
    ):
        monkeypatch.delenv(variable, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
