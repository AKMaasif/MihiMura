from __future__ import annotations

import hashlib
import io
import math
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from app.core.config import settings
from app.services.embeddings import embed_query, embed_texts, embeddings_configured
from app.supabase_client import service_client, supabase_configured

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def knowledge_configured() -> bool:
    return bool(supabase_configured() and embeddings_configured())


def knowledge_database_ready() -> bool:
    if not supabase_configured():
        return False
    try:
        service_client().table("knowledge_documents").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def ingestion_jobs_database_ready() -> bool:
    if not supabase_configured():
        return False
    try:
        service_client().table("knowledge_ingestion_jobs").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_pages(data: bytes, filename: str, mime_type: str | None = None) -> list[dict[str, Any]]:
    suffix = Path(filename or "document").suffix.lower()
    mime = (mime_type or "").lower()
    if suffix == ".pdf" or mime == "application/pdf":
        if PdfReader is None:
            raise RuntimeError("PDF ingestion requires the pypdf package")
        reader = PdfReader(io.BytesIO(data))
        pages: list[dict[str, Any]] = []
        for index, page in enumerate(reader.pages, start=1):
            text = _normalize_text(page.extract_text() or "")
            if text:
                pages.append({"page": index, "text": text})
        if not pages:
            raise ValueError(
                "No extractable text was found in the PDF. Scanned/image-only PDFs need OCR before ingestion."
            )
        return pages

    if suffix in SUPPORTED_TEXT_SUFFIXES or mime.startswith("text/") or not suffix:
        text = _normalize_text(_decode_text(data))
        if not text:
            raise ValueError("The uploaded document contains no readable text")
        return [{"page": None, "text": text}]

    raise ValueError(
        "Unsupported knowledge file. Use a text-based PDF, TXT, MD, CSV, TSV or JSON file."
    )


def _split_long_piece(piece: str, max_chars: int) -> list[str]:
    piece = piece.strip()
    if len(piece) <= max_chars:
        return [piece] if piece else []
    sentences = re.split(r"(?<=[.!?。！？])\s+", piece)
    out: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                out.append(current.strip())
                current = ""
            for start in range(0, len(sentence), max_chars):
                out.append(sentence[start : start + max_chars].strip())
            continue
        candidate = sentence if not current else current + " " + sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                out.append(current.strip())
            current = sentence
    if current:
        out.append(current.strip())
    return [x for x in out if x]


def chunk_pages(
    pages: Iterable[dict[str, Any]],
    *,
    max_chars: int | None = None,
    overlap_chars: int | None = None,
) -> list[dict[str, Any]]:
    max_chars = max(500, int(max_chars or settings.RAG_CHUNK_CHARS))
    overlap_chars = max(0, min(int(overlap_chars or settings.RAG_CHUNK_OVERLAP_CHARS), max_chars // 3))
    chunks: list[dict[str, Any]] = []

    for page in pages:
        page_no = page.get("page")
        text = _normalize_text(str(page.get("text") or ""))
        if not text:
            continue
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
        units: list[str] = []
        for paragraph in paragraphs or [text]:
            units.extend(_split_long_piece(paragraph, max_chars))

        current = ""
        for unit in units:
            candidate = unit if not current else current + "\n\n" + unit
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append({"content": current.strip(), "page_start": page_no, "page_end": page_no})
            if overlap_chars and current:
                tail = current[-overlap_chars:].strip()
                current = (tail + "\n\n" + unit).strip()
                if len(current) > max_chars:
                    current = unit
            else:
                current = unit
        if current:
            chunks.append({"content": current.strip(), "page_start": page_no, "page_end": page_no})

    # Remove accidental duplicate chunks while preserving order.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for chunk in chunks:
        key = hashlib.sha1(chunk["content"].encode("utf-8")).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    for index, chunk in enumerate(unique):
        chunk["chunk_index"] = index
        chunk["token_estimate"] = max(1, math.ceil(len(chunk["content"]) / 4))
    return unique


def _table(name: str):
    return service_client().table(name)


def _storage_upload(path: str, data: bytes, mime_type: str) -> None:
    service_client().storage.from_(settings.SUPABASE_KNOWLEDGE_BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": mime_type or "application/octet-stream", "upsert": "true"},
    )


def _document_by_checksum(checksum: str) -> dict[str, Any] | None:
    rows = _table("knowledge_documents").select("*").eq("checksum_sha256", checksum).limit(1).execute().data or []
    return rows[0] if rows else None


def ingest_knowledge_document(
    *,
    data: bytes,
    filename: str,
    mime_type: str,
    title: str,
    authority: str,
    authority_tier: int = 2,
    document_type: str = "guidance",
    crop: str | None = None,
    language: str = "English",
    region: str | None = None,
    district: str | None = None,
    source_url: str | None = None,
    version_label: str | None = None,
    published_at: str | None = None,
    uploaded_by: str | None = None,
    status: str = "published",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not supabase_configured():
        raise RuntimeError("Supabase is not configured")
    if not embeddings_configured():
        raise RuntimeError("Gemini embeddings are not configured")
    if not data:
        raise ValueError("The knowledge document is empty")

    checksum = hashlib.sha256(data).hexdigest()
    existing = _document_by_checksum(checksum)
    if existing:
        chunk_rows = _table("knowledge_chunks").select("id").eq("document_id", existing["id"]).execute().data or []
        return {
            "document": existing,
            "chunk_count": len(chunk_rows),
            "duplicate": True,
        }

    pages = extract_pages(data, filename, mime_type)
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("No searchable chunks could be created from the document")

    doc_id = f"kdoc_{uuid4().hex[:16]}"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name or "document")[:140]
    storage_path = f"{doc_id}/{safe_name}"
    _storage_upload(storage_path, data, mime_type)

    doc_row = {
        "id": doc_id,
        "title": title.strip() or Path(filename).stem,
        "authority": authority.strip() or "Unspecified source",
        "authority_tier": max(1, min(int(authority_tier), 4)),
        "document_type": document_type.strip() or "guidance",
        "crop": crop.strip() if crop else None,
        "language": language.strip() or "English",
        "region": region.strip() if region else None,
        "district": district.strip() if district else None,
        "source_url": source_url.strip() if source_url else None,
        "version_label": version_label.strip() if version_label else None,
        "published_at": published_at or None,
        "mime_type": mime_type or "application/octet-stream",
        "original_file_name": Path(filename).name,
        "storage_path": storage_path,
        "checksum_sha256": checksum,
        "status": status if status in {"draft", "published", "archived"} else "published",
        "metadata": metadata or {},
        "uploaded_by": uploaded_by,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _table("knowledge_documents").insert(doc_row).execute()

    try:
        batch_size = max(1, min(settings.RAG_EMBED_BATCH_SIZE, 64))
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = embed_texts(
                [x["content"] for x in batch],
                task_type="RETRIEVAL_DOCUMENT",
                title=doc_row["title"],
            )
            rows = []
            for chunk, vector in zip(batch, vectors):
                rows.append(
                    {
                        "id": f"kchunk_{uuid4().hex[:18]}",
                        "document_id": doc_id,
                        "chunk_index": chunk["chunk_index"],
                        "content": chunk["content"],
                        "page_start": chunk.get("page_start"),
                        "page_end": chunk.get("page_end"),
                        "token_estimate": chunk.get("token_estimate"),
                        "embedding": vector,
                        "metadata": {},
                        "created_at": now_iso(),
                    }
                )
            _table("knowledge_chunks").insert(rows).execute()
    except Exception:
        # Avoid leaving a published document with no usable embeddings after a failed ingestion.
        _table("knowledge_documents").delete().eq("id", doc_id).execute()
        try:
            service_client().storage.from_(settings.SUPABASE_KNOWLEDGE_BUCKET).remove([storage_path])
        except Exception:
            pass
        raise

    return {
        "document": doc_row,
        "chunk_count": len(chunks),
        "duplicate": False,
        "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
    }


def list_knowledge_documents(*, status: str | None = None, crop: str | None = None) -> list[dict[str, Any]]:
    query = _table("knowledge_documents").select("*")
    if status:
        query = query.eq("status", status)
    if crop:
        query = query.eq("crop", crop)
    rows = query.execute().data or []
    return sorted(rows, key=lambda x: str(x.get("created_at") or ""), reverse=True)


def update_knowledge_document(document_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "title", "authority", "authority_tier", "document_type", "crop", "language", "region",
        "district", "source_url", "version_label", "published_at", "status", "metadata",
    }
    clean = {k: v for k, v in patch.items() if k in allowed}
    if "authority_tier" in clean:
        clean["authority_tier"] = max(1, min(int(clean["authority_tier"]), 4))
    if "status" in clean and clean["status"] not in {"draft", "published", "archived"}:
        raise ValueError("status must be draft, published or archived")
    clean["updated_at"] = now_iso()
    rows = _table("knowledge_documents").update(clean).eq("id", document_id).execute().data or []
    return rows[0] if rows else None


def delete_knowledge_document(document_id: str) -> bool:
    rows = _table("knowledge_documents").select("id,storage_path").eq("id", document_id).limit(1).execute().data or []
    if not rows:
        return False
    row = rows[0]
    _table("knowledge_documents").delete().eq("id", document_id).execute()
    path = row.get("storage_path")
    if path:
        try:
            service_client().storage.from_(settings.SUPABASE_KNOWLEDGE_BUCKET).remove([path])
        except Exception:
            pass
    return True


def _quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "level": "none",
            "retrieved_count": 0,
            "best_authority_tier": None,
            "requires_expert_verification": True,
        }
    top = results[0]
    tiers = [int(x.get("authority_tier") or 4) for x in results]
    semantic = float(top.get("semantic_similarity") or 0)
    best_tier = min(tiers)
    if best_tier <= 2 and semantic >= 0.62 and len(results) >= 2:
        level = "strong"
    elif semantic >= 0.48:
        level = "moderate"
    else:
        level = "weak"
    return {
        "level": level,
        "retrieved_count": len(results),
        "best_authority_tier": best_tier,
        "top_semantic_similarity": round(semantic, 4),
        "requires_expert_verification": level in {"weak", "none"},
    }


def _query_words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text.casefold())
    tokens = "".join(
        c if unicodedata.category(c)[0] in {"L", "M", "N"} else " " for c in normalized
    ).split()
    stop_words = {"the", "and", "for", "how", "what", "with", "this", "that", "are", "should", "can"}
    return list(dict.fromkeys(word for word in tokens if len(word) >= 3 and word not in stop_words))


def _keyword_rows(
    text: str, crop: str | None, language: str | None, authority: int, kind: str | None, limit: int,
) -> list[dict[str, Any]]:
    terms = _query_words(text[:1500])[:8]
    if not terms:
        return []
    query = _table("knowledge_chunks").select(
        "id,content,page_start,page_end,document_id,knowledge_documents!inner("
        "title,authority,authority_tier,source_url,version_label,published_at,"
        "crop,region,district,status,document_type,language)"
    )
    query = (query.eq("knowledge_documents.status", "published")
             .lte("knowledge_documents.authority_tier", authority)
             .is_("knowledge_documents.region", "null")
             .is_("knowledge_documents.district", "null"))
    if crop:
        query = query.eq("knowledge_documents.crop", crop)
    else:
        query = query.is_("knowledge_documents.crop", "null")
    if language:
        query = query.eq("knowledge_documents.language", language)
    if kind:
        query = query.eq("knowledge_documents.document_type", kind)
    query = query.or_(",".join(f"content.ilike.*{term}*" for term in terms))
    matches: list[tuple[int, dict[str, Any]]] = []
    for raw in query.order("id").limit(80).execute().data or []:
        document = raw.get("knowledge_documents") or {}
        if document.get("status") != "published":
            continue
        count = len(set(terms).intersection(_query_words(str(raw.get("content") or ""))))
        if count >= min(len(terms), 2):
            chunk = {key: val for key, val in raw.items() if key != "knowledge_documents"}
            matches.append((count, {**document, **chunk, "chunk_id": chunk["id"]}))
    matches.sort(key=lambda pair: (-pair[0], int(pair[1].get("authority_tier") or 4)))
    return [row for _, row in matches[:limit]]


def _citations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        excerpt = _normalize_text(str(row.get("content") or ""))
        if len(excerpt) > settings.RAG_MAX_EXCERPT_CHARS:
            excerpt = excerpt[: settings.RAG_MAX_EXCERPT_CHARS].rstrip() + "…"
        page_start, page_end = row.get("page_start"), row.get("page_end")
        if page_start and page_end and page_start != page_end:
            location_label = f"pp. {page_start}-{page_end}"
        elif page_start:
            location_label = f"p. {page_start}"
        else:
            location_label = None
        results.append(
            {
                **row,
                "excerpt": excerpt,
                "location_label": location_label,
                "citation_label": " — ".join(
                    x for x in [str(row.get("authority") or ""), str(row.get("title") or ""), location_label or ""] if x
                ),
            }
        )
    return results


def search_knowledge(
    query: str,
    *,
    crop: str | None = None,
    language: str | None = None,
    max_authority_tier: int = 4,
    document_type: str | None = None,
    top_k: int | None = None,
    strict_language: bool = False,
) -> dict[str, Any]:
    if not query.strip():
        return {"available": False, "results": [], "reason": "empty_query", "evidence_quality": _quality([])}
    if not supabase_configured():
        return {"available": False, "results": [], "reason": "supabase_not_configured", "evidence_quality": _quality([])}

    limit = max(1, min(int(top_k or settings.RAG_TOP_K), 20))
    authority = max(1, min(int(max_authority_tier), 4))
    match_language = language if strict_language else None
    if embeddings_configured():
        try:
            vector = embed_query(query)
            params = {
                "query_text": query,
                "query_embedding": vector,
                "match_count": limit,
                "filter_crop": crop or None,
                # Default is intentionally cross-language. Gemini retrieval embeddings are
                # multilingual, so Sinhala/Tamil questions can retrieve authoritative English
                # material. strict_language can be used by admin/test tools when desired.
                "filter_language": language if strict_language and language else None,
                "max_authority_tier": max(1, min(int(max_authority_tier), 4)),
                "filter_document_type": document_type or None,
            }
            rows = service_client().rpc("search_knowledge_hybrid", params).execute().data or []
            results = _citations(rows)
            return {
                "available": True,
                "retrieval": "hybrid_pgvector_fts",
                "query": query,
                "results": results,
                "evidence_quality": _quality(results),
                "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            }
        except Exception:
            fallback_reason = "vector_search_unavailable"
    else:
        fallback_reason = "embeddings_not_configured"

    try:
        results = _citations(_keyword_rows(query, crop, match_language, authority, document_type, limit))
        return {
            "available": True, "retrieval": "published_keyword", "query": query,
            "results": results, "reason": fallback_reason, "evidence_quality": _quality(results),
        }
    except Exception:
        return {"available": False, "results": [], "reason": "knowledge_search_failed", "evidence_quality": _quality([])}


# ---------------------------------------------------------------------------
# v7.1 asynchronous ingestion jobs
# ---------------------------------------------------------------------------

def _job_table():
    return service_client().table("knowledge_ingestion_jobs")


def _update_ingestion_job(job_id: str, **patch: Any) -> dict[str, Any] | None:
    payload = {**patch, "updated_at": now_iso()}
    rows = _job_table().update(payload).eq("id", job_id).execute().data or []
    return rows[0] if rows else None


def list_ingestion_jobs(*, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        _job_table()
        .select("*,knowledge_documents(title,authority,crop,language,status)")
        .order("created_at", desc=True)
        .limit(max(1, min(int(limit), 100)))
        .execute()
        .data
        or []
    )
    return rows


def get_ingestion_job(job_id: str) -> dict[str, Any] | None:
    rows = (
        _job_table()
        .select("*,knowledge_documents(title,authority,crop,language,status,storage_path,original_file_name,mime_type)")
        .eq("id", job_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _active_job_for_document(document_id: str) -> dict[str, Any] | None:
    rows = (
        _job_table()
        .select("*")
        .eq("document_id", document_id)
        .in_("status", ["queued", "processing", "cancel_requested"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _document_is_complete(document: dict[str, Any]) -> bool:
    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    return bool(metadata.get("ingestion_complete"))


def create_ingestion_job(
    *,
    data: bytes,
    filename: str,
    mime_type: str,
    title: str,
    authority: str,
    authority_tier: int = 2,
    document_type: str = "guidance",
    crop: str | None = None,
    language: str = "English",
    region: str | None = None,
    district: str | None = None,
    source_url: str | None = None,
    version_label: str | None = None,
    published_at: str | None = None,
    uploaded_by: str | None = None,
    status: str = "published",
) -> dict[str, Any]:
    """Create a durable ingestion job and return immediately after upload/metadata creation.

    Expensive PDF parsing/chunk embedding happens later in a FastAPI background task.
    """
    if not supabase_configured():
        raise RuntimeError("Supabase is not configured")
    if not embeddings_configured():
        raise RuntimeError("Gemini embeddings are not configured")
    if not data:
        raise ValueError("The knowledge document is empty")

    requested_status = status if status in {"draft", "published", "archived"} else "published"
    checksum = hashlib.sha256(data).hexdigest()
    existing = _document_by_checksum(checksum)

    if existing:
        active = _active_job_for_document(existing["id"])
        if active:
            return {"accepted": True, "duplicate": False, "document": existing, "job": active, "already_running": True}
        if _document_is_complete(existing):
            chunk_rows = _table("knowledge_chunks").select("id").eq("document_id", existing["id"]).execute().data or []
            return {"accepted": False, "duplicate": True, "document": existing, "chunk_count": len(chunk_rows)}
        # Legacy/partial v7 ingestion: reuse the document and rebuild its chunks.
        doc_id = existing["id"]
        storage_path = existing.get("storage_path") or f"{doc_id}/{re.sub(r'[^A-Za-z0-9._-]+', '_', Path(filename).name)[:140]}"
        _storage_upload(storage_path, data, mime_type)
        _table("knowledge_chunks").delete().eq("document_id", doc_id).execute()
        metadata = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
        metadata = {**metadata, "ingestion_complete": False, "ingestion_restarted_at": now_iso()}
        doc_patch = {
            "title": title.strip() or existing.get("title") or Path(filename).stem,
            "authority": authority.strip() or existing.get("authority") or "Unspecified source",
            "authority_tier": max(1, min(int(authority_tier), 4)),
            "document_type": document_type.strip() or "guidance",
            "crop": crop.strip() if crop else None,
            "language": language.strip() or "English",
            "region": region.strip() if region else None,
            "district": district.strip() if district else None,
            "source_url": source_url.strip() if source_url else None,
            "version_label": version_label.strip() if version_label else None,
            "published_at": published_at or None,
            "mime_type": mime_type or "application/octet-stream",
            "original_file_name": Path(filename).name,
            "storage_path": storage_path,
            "status": "draft",
            "metadata": metadata,
            "updated_at": now_iso(),
        }
        _table("knowledge_documents").update(doc_patch).eq("id", doc_id).execute()
        document = {**existing, **doc_patch}
    else:
        doc_id = f"kdoc_{uuid4().hex[:16]}"
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name or "document")[:140]
        storage_path = f"{doc_id}/{safe_name}"
        _storage_upload(storage_path, data, mime_type)
        document = {
            "id": doc_id,
            "title": title.strip() or Path(filename).stem,
            "authority": authority.strip() or "Unspecified source",
            "authority_tier": max(1, min(int(authority_tier), 4)),
            "document_type": document_type.strip() or "guidance",
            "crop": crop.strip() if crop else None,
            "language": language.strip() or "English",
            "region": region.strip() if region else None,
            "district": district.strip() if district else None,
            "source_url": source_url.strip() if source_url else None,
            "version_label": version_label.strip() if version_label else None,
            "published_at": published_at or None,
            "mime_type": mime_type or "application/octet-stream",
            "original_file_name": Path(filename).name,
            "storage_path": storage_path,
            "checksum_sha256": checksum,
            "status": "draft",
            "metadata": {"ingestion_complete": False},
            "uploaded_by": uploaded_by,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        _table("knowledge_documents").insert(document).execute()

    job = {
        "id": f"kjob_{uuid4().hex[:18]}",
        "document_id": doc_id,
        "status": "queued",
        "stage": "queued",
        "progress_percent": 2,
        "total_chunks": 0,
        "processed_chunks": 0,
        "current_batch": 0,
        "total_batches": 0,
        "requested_document_status": requested_status,
        "error_message": None,
        "details": {"filename": Path(filename).name, "mime_type": mime_type or "application/octet-stream"},
        "created_by": uploaded_by,
        "heartbeat_at": now_iso(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _job_table().insert(job).execute()
    return {"accepted": True, "duplicate": False, "document": document, "job": job, "already_running": False}


def _embed_batch_with_retry(texts: list[str], *, title: str) -> list[list[float]]:
    attempts = max(1, int(getattr(settings, "RAG_EMBED_MAX_RETRIES", 3)))
    base_delay = max(0.25, float(getattr(settings, "RAG_EMBED_RETRY_BASE_SECONDS", 1.5)))
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return embed_texts(texts, task_type="RETRIEVAL_DOCUMENT", title=title)
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(base_delay * (2 ** (attempt - 1)))
    assert last_exc is not None
    raise last_exc


def run_ingestion_job(*, job_id: str, data: bytes, filename: str, mime_type: str) -> None:
    """Execute a queued ingestion job and persist progress after every stage/batch."""
    job = get_ingestion_job(job_id)
    if not job:
        return
    doc_id = str(job["document_id"])
    document = job.get("knowledge_documents") or {}
    requested_status = str(job.get("requested_document_status") or "published")
    try:
        _update_ingestion_job(
            job_id,
            status="processing",
            stage="extracting_text",
            progress_percent=5,
            started_at=now_iso(),
            heartbeat_at=now_iso(),
            error_message=None,
        )
        pages = extract_pages(data, filename, mime_type)

        _update_ingestion_job(job_id, stage="chunking", progress_percent=10, heartbeat_at=now_iso())
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No searchable chunks could be created from the document")

        batch_size = max(1, min(int(settings.RAG_EMBED_BATCH_SIZE), 64))
        total_chunks = len(chunks)
        total_batches = math.ceil(total_chunks / batch_size)
        _table("knowledge_chunks").delete().eq("document_id", doc_id).execute()
        _update_ingestion_job(
            job_id,
            stage="embedding",
            progress_percent=15,
            total_chunks=total_chunks,
            processed_chunks=0,
            current_batch=0,
            total_batches=total_batches,
            heartbeat_at=now_iso(),
        )

        title = str(document.get("title") or Path(filename).stem)
        processed = 0
        for batch_number, start in enumerate(range(0, total_chunks, batch_size), start=1):
            latest = get_ingestion_job(job_id) or {}
            if latest.get("status") == "cancel_requested":
                _update_ingestion_job(job_id, status="cancelled", stage="cancelled", completed_at=now_iso(), heartbeat_at=now_iso())
                return

            batch = chunks[start : start + batch_size]
            _update_ingestion_job(
                job_id,
                stage="embedding",
                current_batch=batch_number,
                heartbeat_at=now_iso(),
                details={
                    "filename": Path(filename).name,
                    "mime_type": mime_type or "application/octet-stream",
                    "message": f"Embedding batch {batch_number} of {total_batches}",
                },
            )
            vectors = _embed_batch_with_retry([x["content"] for x in batch], title=title)
            rows = []
            for chunk, vector in zip(batch, vectors):
                rows.append({
                    "id": f"kchunk_{uuid4().hex[:18]}",
                    "document_id": doc_id,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "page_start": chunk.get("page_start"),
                    "page_end": chunk.get("page_end"),
                    "token_estimate": chunk.get("token_estimate"),
                    "embedding": vector,
                    "metadata": {},
                    "created_at": now_iso(),
                })
            _table("knowledge_chunks").insert(rows).execute()
            processed += len(rows)
            progress = min(95, 15 + round((processed / total_chunks) * 80))
            _update_ingestion_job(
                job_id,
                stage="embedding",
                progress_percent=progress,
                processed_chunks=processed,
                current_batch=batch_number,
                total_batches=total_batches,
                heartbeat_at=now_iso(),
            )

        _update_ingestion_job(job_id, stage="finalizing_index", progress_percent=97, heartbeat_at=now_iso())
        current_doc_rows = _table("knowledge_documents").select("metadata").eq("id", doc_id).limit(1).execute().data or []
        metadata = current_doc_rows[0].get("metadata") if current_doc_rows and isinstance(current_doc_rows[0].get("metadata"), dict) else {}
        metadata = {
            **metadata,
            "ingestion_complete": True,
            "total_chunks": total_chunks,
            "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
            "last_indexed_at": now_iso(),
        }
        _table("knowledge_documents").update({
            "status": requested_status,
            "metadata": metadata,
            "updated_at": now_iso(),
        }).eq("id", doc_id).execute()
        _update_ingestion_job(
            job_id,
            status="completed",
            stage="completed",
            progress_percent=100,
            processed_chunks=total_chunks,
            total_chunks=total_chunks,
            current_batch=total_batches,
            total_batches=total_batches,
            completed_at=now_iso(),
            heartbeat_at=now_iso(),
            error_message=None,
        )
    except Exception as exc:
        # Keep the original file and partial/draft document so an admin can inspect/retry.
        _table("knowledge_documents").update({"status": "draft", "updated_at": now_iso()}).eq("id", doc_id).execute()
        _update_ingestion_job(
            job_id,
            status="failed",
            stage="failed",
            error_message=str(exc)[:2000],
            completed_at=now_iso(),
            heartbeat_at=now_iso(),
        )


def request_ingestion_cancel(job_id: str) -> dict[str, Any] | None:
    job = get_ingestion_job(job_id)
    if not job:
        return None
    if job.get("status") not in {"queued", "processing"}:
        return job
    return _update_ingestion_job(job_id, status="cancel_requested", stage="cancel_requested", heartbeat_at=now_iso())


def load_job_document_bytes(job_id: str) -> tuple[dict[str, Any], bytes, str, str]:
    job = get_ingestion_job(job_id)
    if not job:
        raise ValueError("Ingestion job not found")
    document = job.get("knowledge_documents") or {}
    storage_path = str(document.get("storage_path") or "")
    if not storage_path:
        raise ValueError("Knowledge document has no stored source file")
    raw = service_client().storage.from_(settings.SUPABASE_KNOWLEDGE_BUCKET).download(storage_path)
    if not isinstance(raw, (bytes, bytearray)):
        raw = bytes(raw)
    return job, bytes(raw), str(document.get("original_file_name") or "knowledge-document"), str(document.get("mime_type") or "application/octet-stream")


def create_retry_job(job_id: str, *, created_by: str | None = None) -> dict[str, Any]:
    old = get_ingestion_job(job_id)
    if not old:
        raise ValueError("Ingestion job not found")
    document = old.get("knowledge_documents") or {}
    doc_id = str(old["document_id"])
    active = _active_job_for_document(doc_id)
    if active:
        return active
    _table("knowledge_chunks").delete().eq("document_id", doc_id).execute()
    _table("knowledge_documents").update({"status": "draft", "updated_at": now_iso()}).eq("id", doc_id).execute()
    new_job = {
        "id": f"kjob_{uuid4().hex[:18]}",
        "document_id": doc_id,
        "status": "queued",
        "stage": "queued",
        "progress_percent": 2,
        "total_chunks": 0,
        "processed_chunks": 0,
        "current_batch": 0,
        "total_batches": 0,
        "requested_document_status": str(old.get("requested_document_status") or "published"),
        "error_message": None,
        "details": {"retry_of": job_id, "filename": document.get("original_file_name")},
        "created_by": created_by,
        "heartbeat_at": now_iso(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _job_table().insert(new_job).execute()
    return new_job
