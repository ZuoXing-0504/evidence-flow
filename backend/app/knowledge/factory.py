from functools import lru_cache

from app.core.config import Settings, get_settings
from app.knowledge.embeddings import DashScopeEmbedder, DeterministicEmbedder, Embedder
from app.knowledge.semantic import SemanticKnowledgeStore
from app.knowledge.vector import InMemoryVectorBackend, MilvusVectorBackend, VectorBackend


def build_knowledge_store(settings: Settings) -> SemanticKnowledgeStore:
    if settings.embedding_provider == "dashscope":
        embedder: Embedder = DashScopeEmbedder(
            api_key=settings.dashscope_api_key.get_secret_value(),
            base_url=settings.dashscope_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            timeout=settings.provider_timeout_seconds,
        )
    else:
        embedder = DeterministicEmbedder(settings.embedding_dimension)

    if settings.vector_store_provider == "milvus":
        backend: VectorBackend = MilvusVectorBackend(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            dimension=embedder.dimension,
        )
    else:
        backend = InMemoryVectorBackend()

    return SemanticKnowledgeStore(
        embedder,
        backend,
        collection_prefix=settings.milvus_collection_prefix,
    )


@lru_cache
def get_knowledge_store() -> SemanticKnowledgeStore:
    return build_knowledge_store(get_settings())
