from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.knowledge_base import search_knowledge

_SOURCES = json.loads(
    (Path(__file__).resolve().parents[1] / "knowledge" / "approved_sources.json").read_text(encoding="utf-8")
)


def _static_metadata(crop: str) -> list[dict[str, Any]]:
    key = (crop or "").strip().lower()
    selected = list(_SOURCES.get("general", []))
    if key in _SOURCES:
        selected.extend(_SOURCES[key])
    out: list[dict[str, Any]] = []
    for item in selected:
        out.append(
            {
                **item,
                "source_type": "approved_source_registry",
                "retrieval_note": "Reference metadata only; the source text was not retrieved from the RAG index in this turn.",
                "authority_tier": 1,
            }
        )
    return out


def retrieve_approved_knowledge(
    crop: str,
    question: str,
    *,
    language: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Retrieve curated agronomy evidence with a safe metadata fallback.

    Phase 2 first searches the Supabase pgvector + PostgreSQL FTS knowledge index.
    If the index is empty/unavailable, the old approved-source registry remains as a
    transparent pointer to official sources; it is never treated as retrieved content.
    """
    rag = search_knowledge(question, crop=crop or None, language=language, top_k=8)
    if rag.get("available") and rag.get("results"):
        retrieval = rag.get("retrieval") or "hybrid_pgvector_fts"
        documents: list[dict[str, Any]] = []
        for row in rag["results"]:
            documents.append(
                {
                    "authority": row.get("authority"),
                    "title": row.get("title"),
                    "url": row.get("source_url"),
                    "scope": row.get("excerpt"),
                    "excerpt": row.get("excerpt"),
                    "page": row.get("location_label"),
                    "citation_label": row.get("citation_label"),
                    "authority_tier": row.get("authority_tier"),
                    "document_type": row.get("document_type"),
                    "language": row.get("language"),
                    "crop": row.get("crop"),
                    "semantic_similarity": row.get("semantic_similarity"),
                    "hybrid_score": row.get("hybrid_score"),
                    "chunk_id": row.get("chunk_id"),
                    "document_id": row.get("document_id"),
                    "source_type": "keyword_rag" if retrieval == "published_keyword" else "hybrid_rag",
                    "safe_note": "Use only claims supported by this retrieved excerpt; rate-sensitive or hazardous guidance still requires the current official label/protocol.",
                }
            )
        return {
            "query": question,
            "crop": crop or "not selected",
            "location": location,
            "retrieval": retrieval,
            "documents": documents,
            "evidence_quality": rag.get("evidence_quality") or {},
            "embedding_model": rag.get("embedding_model"),
            "rag_status": rag.get("reason"),
            "grounding_rule": "Use retrieved excerpts as evidence. Do not invent a rate, product approval, warning, price or field measurement that is not explicitly supported by current evidence.",
        }

    return {
        "query": question,
        "crop": crop or "not selected",
        "location": location,
        "retrieval": "approved_source_registry_fallback",
        "documents": _static_metadata(crop),
        "evidence_quality": rag.get("evidence_quality") or {"level": "none"},
        "rag_status": rag.get("reason") or "no_indexed_match",
        "grounding_rule": "Consequential rates and chemical choices require a current approved source. Registry links are pointers only and are not a substitute for retrieved/verified source text.",
    }
