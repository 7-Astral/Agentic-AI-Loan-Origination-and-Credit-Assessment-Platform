import asyncio
from functools import lru_cache

from fastembed import TextEmbedding

from app.core.config import get_settings
from app.models.policy import EMBEDDING_DIMENSIONS


@lru_cache
def _model() -> TextEmbedding:
    settings = get_settings()
    return TextEmbedding(
        model_name=settings.policy_embedding_model,
        cache_dir=settings.policy_embedding_cache_dir or None,
    )


def _check(vectors: list[list[float]]) -> list[list[float]]:
    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(vector)}.")
    return vectors


def _embed_documents(texts: list[str]) -> list[list[float]]:
    return _check([vector.tolist() for vector in _model().embed(texts)])


def _embed_query(text: str) -> list[float]:
    return _check([vector.tolist() for vector in _model().query_embed(text)])[0]


async def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(_embed_documents, texts)


async def create_query_embedding(text: str) -> list[float]:
    return await asyncio.to_thread(_embed_query, text)
