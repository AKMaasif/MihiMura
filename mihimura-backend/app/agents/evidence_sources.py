"""Build the "sources" list shown under an answer from the evidence actually used."""

from __future__ import annotations

from typing import Any

MARKET_REGISTRY_SOURCE = {"name": "MihiMura market-channel registry", "freshness": "local registry; no live price feed connected"}


def knowledge_sources(knowledge: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    retrieval = str(knowledge.get("retrieval") or "")
    items: list[dict[str, Any]] = []
    for doc in (knowledge.get("documents") or [])[:limit]:
        page = doc.get("page")
        if retrieval == "hybrid_pgvector_fts" or doc.get("source_type") == "hybrid_rag":
            freshness = "indexed evidence" + (f" · {page}" if page else "")
        elif retrieval == "published_keyword":
            freshness = "keyword match · verify before acting" + (f" · {page}" if page else "")
        else:
            freshness = "reference link only · source text not retrieved in this turn"
        items.append({
            "name": f"{doc.get('authority')}: {doc.get('title')}",
            "freshness": freshness,
            "url": doc.get("url"),
            "source_type": doc.get("source_type") or retrieval,
            "citation": doc.get("citation_label"),
            "authority_tier": doc.get("authority_tier"),
        })
    return items


def evidence_sources(weather: dict[str, Any], climate: dict[str, Any], knowledge: dict[str, Any], *, market_used: bool = False) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if weather.get("source") and weather.get("status") != "not_requested":
        live = bool(weather.get("live"))
        items.append({
            "name": weather.get("source", "Open-Meteo"),
            "freshness": weather.get("retrieved_at", "current request") if live else "UNAVAILABLE / demo fallback - not valid current weather",
            "source_type": "live_weather" if live else "weather_fallback",
            "status": weather.get("status") or ("success" if live else "unavailable"),
        })
    if climate.get("source") and climate.get("status") != "not_requested":
        live = bool(climate.get("live"))
        items.append({
            "name": climate.get("source", "NASA POWER"),
            "freshness": (climate.get("period") or {}).get("end", "recent baseline") if live else "unavailable in this request",
            "source_type": "climate_baseline",
            "status": climate.get("status") or ("success" if live else "unavailable"),
        })
    items.extend(knowledge_sources(knowledge))
    if market_used:
        items.append(dict(MARKET_REGISTRY_SOURCE))
    return items
