from __future__ import annotations

import time
from typing import Any, Callable


def execute_tool(name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        data = fn(*args, **kwargs)
        elapsed = round((time.perf_counter() - started) * 1000)
        status = "success"
        if isinstance(data, dict):
            raw = str(data.get("status") or "").lower()
            if raw in {"unavailable", "error", "failed"}:
                status = raw
            elif data.get("live") is False and name in {"weather", "climate"}:
                status = "unavailable"
        return {"name": name, "status": status, "latency_ms": elapsed, "data": data, "error": None}
    except Exception as exc:
        return {
            "name": name,
            "status": "error",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "data": {},
            "error": str(exc),
        }
