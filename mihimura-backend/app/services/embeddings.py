from __future__ import annotations

from typing import Any, Iterable

from app.core.ai import get_gemini_client
from app.core.config import settings

try:
    from google.genai import types
except ImportError:  # pragma: no cover - dependency guard for source-only checks
    types = None  # type: ignore[assignment]


class EmbeddingUnavailable(RuntimeError):
    pass


def embeddings_configured() -> bool:
    return bool(get_gemini_client() is not None and types is not None and settings.GEMINI_EMBEDDING_MODEL)


def _values(item: Any) -> list[float]:
    values = getattr(item, "values", None)
    if values is None and isinstance(item, dict):
        values = item.get("values")
    if not values:
        raise EmbeddingUnavailable("Embedding provider returned an empty vector")
    return [float(x) for x in values]


def embed_texts(
    texts: Iterable[str],
    *,
    task_type: str,
    title: str | None = None,
) -> list[list[float]]:
    clean = [str(x).strip() for x in texts if str(x).strip()]
    if not clean:
        return []
    client = get_gemini_client()
    if client is None or types is None:
        raise EmbeddingUnavailable("Gemini embeddings are not configured")

    kwargs: dict[str, Any] = {
        "task_type": task_type,
        "output_dimensionality": settings.EMBEDDING_DIMENSION,
        # Prevent a single provider/network call from leaving an ingestion batch pending forever.
        "http_options": types.HttpOptions(timeout=max(1000, int(settings.RAG_EMBED_TIMEOUT_MS))),
    }
    if title and task_type == "RETRIEVAL_DOCUMENT":
        kwargs["title"] = title[:512]

    result = client.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=clean,
        config=types.EmbedContentConfig(**kwargs),
    )
    raw = getattr(result, "embeddings", None)
    if raw is None:
        single = getattr(result, "embedding", None)
        raw = [single] if single is not None else None
    if not raw:
        raise EmbeddingUnavailable("Embedding provider returned no embeddings")

    vectors = [_values(item) for item in raw]
    if len(vectors) != len(clean):
        raise EmbeddingUnavailable(
            f"Embedding count mismatch: requested {len(clean)}, received {len(vectors)}"
        )
    for vector in vectors:
        if len(vector) != settings.EMBEDDING_DIMENSION:
            raise EmbeddingUnavailable(
                f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIMENSION}, received {len(vector)}"
            )
    return vectors


def embed_query(text: str) -> list[float]:
    vectors = embed_texts([text], task_type="RETRIEVAL_QUERY")
    if not vectors:
        raise EmbeddingUnavailable("Cannot embed an empty query")
    return vectors[0]
