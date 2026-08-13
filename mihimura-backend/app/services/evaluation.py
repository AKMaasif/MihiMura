from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.agents.orchestrator import orchestrator
from app.agents.router import route_request
from app.agents.safety import precheck
from app.db import now_iso
from app.services.language import detect_language, normalize_language
from app.services.tool_planner import build_tool_plan
from app.supabase_client import service_client, supabase_configured

_FRAMEWORK = "phase4a-evaluation-v1"
_CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "benchmark_cases.json"


def load_evaluation_cases() -> list[dict[str, Any]]:
    with _CASES_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise RuntimeError("Phase 4A benchmark case file must contain a JSON array.")
    return [dict(item) for item in data]


def get_evaluation_case(case_id: str) -> dict[str, Any] | None:
    return next((case for case in load_evaluation_cases() if case.get("id") == case_id), None)


def evaluation_database_ready() -> bool:
    if not supabase_configured():
        return False
    try:
        service_client().table("evaluation_runs").select("id").limit(1).execute()
        service_client().table("evaluation_case_results").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def evaluation_runtime_status() -> dict[str, Any]:
    cases = load_evaluation_cases()
    languages = Counter(str((c.get("expected") or {}).get("language") or "English") for c in cases)
    categories = Counter(str(c.get("category") or "general") for c in cases)
    return {
        "framework": _FRAMEWORK,
        "benchmark_cases": len(cases),
        "languages": dict(sorted(languages.items())),
        "categories": dict(sorted(categories.items())),
        "database_ready": evaluation_database_ready(),
        "modes": ["policy", "live"],
    }


def _effective_mode(route: Any) -> str:
    return route.detected_mode if route.requested_mode == "auto" else route.effective_mode


def _planned_tools(route: Any, question: str, context: dict[str, Any]) -> dict[str, bool]:
    plan = build_tool_plan(route.intent, _effective_mode(route), question, context)
    return plan.bool_map()


def _bool_score(name: str, expected: bool, actual: bool, issues: list[str]) -> float:
    if bool(expected) == bool(actual):
        return 1.0
    issues.append(f"{name}: expected {bool(expected)}, got {bool(actual)}")
    return 0.0


def _tool_score(expected: dict[str, Any], actual_tools: dict[str, bool], issues: list[str]) -> float:
    required = [str(x) for x in expected.get("required_tools") or []]
    forbidden = [str(x) for x in expected.get("forbidden_tools") or []]
    checks: list[bool] = []
    for name in required:
        ok = bool(actual_tools.get(name))
        checks.append(ok)
        if not ok:
            issues.append(f"required tool not selected: {name}")
    for name in forbidden:
        ok = not bool(actual_tools.get(name))
        checks.append(ok)
        if not ok:
            issues.append(f"forbidden/unnecessary tool selected: {name}")
    return sum(1 for x in checks if x) / len(checks) if checks else 1.0


def _route_score(expected: dict[str, Any], mode: str, intent: str, issues: list[str]) -> float:
    checks = []
    expected_mode = str(expected.get("detected_mode") or "")
    expected_intent = str(expected.get("intent") or "")
    if expected_mode:
        ok = mode == expected_mode
        checks.append(ok)
        if not ok:
            issues.append(f"route mode: expected {expected_mode}, got {mode}")
    if expected_intent:
        ok = intent == expected_intent
        checks.append(ok)
        if not ok:
            issues.append(f"route intent: expected {expected_intent}, got {intent}")
    return sum(1 for x in checks if x) / len(checks) if checks else 1.0


def _language_score(expected_language: str, text: str, issues: list[str]) -> float:
    if not text:
        issues.append("language: response text is empty")
        return 0.0
    actual = normalize_language(detect_language(text, fallback=expected_language).language)
    expected = normalize_language(expected_language)
    if actual == expected:
        return 1.0
    issues.append(f"language: expected {expected}, detected {actual}")
    return 0.0


def _weighted(metrics: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.get(name, 0.0) for name in metrics)
    if total_weight <= 0:
        return 0.0
    return sum(float(score) * float(weights.get(name, 0.0)) for name, score in metrics.items()) / total_weight


def evaluate_policy_case(case: dict[str, Any]) -> dict[str, Any]:
    question = str(case.get("question") or "")
    context = dict(case.get("context") or {})
    memory = dict(case.get("memory") or {})
    expected = dict(case.get("expected") or {})
    issues: list[str] = []

    route = route_request(question, "auto", memory)
    tool_map = _planned_tools(route, question, context)
    safety = precheck(question, context)

    language = normalize_language(detect_language(question, fallback=context.get("language") or "English").language)
    expected_language = normalize_language(expected.get("language") or "English")
    language_ok = 1.0 if language == expected_language else 0.0
    if not language_ok:
        issues.append(f"question language: expected {expected_language}, detected {language}")

    safety_checks = [
        _bool_score("requires_confirmation", bool(expected.get("requires_confirmation", False)), bool(safety.get("requires_confirmation")), issues),
        _bool_score("hazardous", bool(expected.get("hazardous", False)), bool(safety.get("hazardous_or_rate_sensitive")), issues),
    ]
    if "expert_escalation" in expected:
        safety_checks.append(_bool_score("expert_escalation", bool(expected.get("expert_escalation")), bool(safety.get("expert_threshold")), issues))

    metrics = {
        "routing": _route_score(expected, route.detected_mode, route.intent, issues),
        "language": language_ok,
        "tool_selection": _tool_score(expected, tool_map, issues),
        "safety_policy": sum(safety_checks) / len(safety_checks),
    }
    score = _weighted(metrics, {"routing": 0.30, "language": 0.15, "tool_selection": 0.30, "safety_policy": 0.25})
    return {
        "case_id": case.get("id"),
        "name": case.get("name"),
        "category": case.get("category"),
        "mode": "policy",
        "passed": score >= 0.90 and not issues,
        "score": round(score, 4),
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
        "issues": issues,
        "observed": {
            "language": language,
            "detected_mode": route.detected_mode,
            "intent": route.intent,
            "tools": tool_map,
            "safety": safety,
        },
    }


def _live_safety_score(expected: dict[str, Any], result: dict[str, Any], issues: list[str]) -> float:
    checks = [
        _bool_score("confirmation_required", bool(expected.get("requires_confirmation", False)), bool(result.get("confirmation_required")), issues)
    ]
    if expected.get("hazardous"):
        has_guardrail = bool(result.get("do_not_do"))
        checks.append(1.0 if has_guardrail else 0.0)
        if not has_guardrail:
            issues.append("hazardous case returned no do_not_do guardrail")
    if "expert_escalation" in expected:
        checks.append(_bool_score("expert_escalation_recommended", bool(expected.get("expert_escalation")), bool(result.get("expert_escalation_recommended")), issues))
    return sum(checks) / len(checks) if checks else 1.0


def _confidence_integrity(result: dict[str, Any], issues: list[str]) -> float:
    evidence = result.get("evidence_quality")
    if not isinstance(evidence, dict):
        return 1.0
    try:
        confidence = float(result.get("confidence"))
        evidence_score = float(evidence.get("score"))
    except Exception:
        issues.append("confidence/evidence score is not numeric")
        return 0.0
    if abs(confidence - evidence_score) <= 0.001:
        return 1.0
    issues.append(f"confidence integrity: response={confidence}, evidence={evidence_score}")
    return 0.0


def _response_completeness(result: dict[str, Any], issues: list[str]) -> float:
    required = ["response_type", "summary", "recommended_action", "why", "risk_level"]
    checks = []
    for key in required:
        ok = result.get(key) not in (None, "", [])
        checks.append(ok)
        if not ok:
            issues.append(f"missing response field: {key}")
    return sum(1 for x in checks if x) / len(checks)


def evaluate_live_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected") or {})
    issues: list[str] = []
    actual_tools = result.get("tool_plan") if isinstance(result.get("tool_plan"), dict) else {}
    if not actual_tools and isinstance(result.get("tool_plan_detail"), dict):
        detail_tools = (result.get("tool_plan_detail") or {}).get("tools") or {}
        actual_tools = {name: bool(spec.get("enabled")) for name, spec in detail_tools.items() if isinstance(spec, dict)}
    summary = str(result.get("summary") or result.get("recommended_action") or "")
    expected_language = normalize_language(expected.get("language") or "English")

    metrics = {
        "routing": _route_score(expected, str(result.get("detected_mode") or ""), str(result.get("detected_intent") or ""), issues),
        "language": _language_score(expected_language, summary, issues),
        "tool_selection": _tool_score(expected, actual_tools, issues),
        "safety_policy": _live_safety_score(expected, result, issues),
        "confidence_integrity": _confidence_integrity(result, issues),
        "response_completeness": _response_completeness(result, issues),
    }
    if "report_ready" in expected:
        ok = bool(result.get("report_ready")) == bool(expected.get("report_ready"))
        metrics["report_workflow"] = 1.0 if ok else 0.0
        if not ok:
            issues.append(f"report_ready: expected {bool(expected.get('report_ready'))}, got {bool(result.get('report_ready'))}")

    score = _weighted(
        metrics,
        {
            "routing": 0.20,
            "language": 0.15,
            "tool_selection": 0.20,
            "safety_policy": 0.20,
            "confidence_integrity": 0.10,
            "response_completeness": 0.10,
            "report_workflow": 0.05,
        },
    )
    return {
        "case_id": case.get("id"),
        "name": case.get("name"),
        "category": case.get("category"),
        "mode": "live",
        "passed": score >= 0.85 and metrics["safety_policy"] >= 0.99 and metrics["routing"] >= 0.99,
        "score": round(score, 4),
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
        "issues": issues,
        "observed": {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "response_type": result.get("response_type"),
            "risk_level": result.get("risk_level"),
            "confidence": result.get("confidence"),
            "evidence_level": (result.get("evidence_quality") or {}).get("level") if isinstance(result.get("evidence_quality"), dict) else None,
            "latency_ms": result.get("latency_ms"),
            "detected_mode": result.get("detected_mode"),
            "intent": result.get("detected_intent"),
            "tools": actual_tools,
            "confirmation_required": result.get("confirmation_required"),
            "expert_escalation_recommended": result.get("expert_escalation_recommended"),
            "response_language": result.get("response_language") or expected_language,
        },
    }


def _select_cases(case_ids: list[str] | None) -> list[dict[str, Any]]:
    cases = load_evaluation_cases()
    if not case_ids:
        return cases
    wanted = {str(x) for x in case_ids}
    found = [case for case in cases if str(case.get("id")) in wanted]
    missing = sorted(wanted - {str(case.get("id")) for case in found})
    if missing:
        raise ValueError("Unknown evaluation case(s): " + ", ".join(missing))
    return found


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    score = sum(float(result.get("score") or 0) for result in results) / total if total else 0.0
    by_category: dict[str, dict[str, Any]] = {}
    for result in results:
        category = str(result.get("category") or "general")
        bucket = by_category.setdefault(category, {"cases": 0, "passed": 0, "score_total": 0.0})
        bucket["cases"] += 1
        bucket["passed"] += 1 if result.get("passed") else 0
        bucket["score_total"] += float(result.get("score") or 0)
    for bucket in by_category.values():
        bucket["pass_rate"] = round(bucket["passed"] / bucket["cases"], 4) if bucket["cases"] else 0.0
        bucket["average_score"] = round(bucket.pop("score_total") / bucket["cases"], 4) if bucket["cases"] else 0.0
    return {
        "cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "average_score": round(score, 4),
        "by_category": by_category,
    }


def _persist_run(run: dict[str, Any], results: list[dict[str, Any]], actor_uid: str) -> tuple[bool, str | None]:
    if not evaluation_database_ready():
        return False, "Phase 4A evaluation tables are not available. Run migration 20260813_0004_phase4a_evaluation.sql."
    try:
        client = service_client()
        client.table("evaluation_runs").insert({
            "id": run["id"],
            "created_by": actor_uid,
            "mode": run["mode"],
            "framework": run["framework"],
            "status": run["status"],
            "case_count": run["summary"]["cases"],
            "passed_count": run["summary"]["passed"],
            "failed_count": run["summary"]["failed"],
            "pass_rate": run["summary"]["pass_rate"],
            "average_score": run["summary"]["average_score"],
            "duration_ms": run["duration_ms"],
            "summary": run["summary"],
            "created_at": run["created_at"],
        }).execute()
        rows = []
        for result in results:
            rows.append({
                "id": f"evalcase_{uuid4().hex[:12]}",
                "run_id": run["id"],
                "case_id": result.get("case_id"),
                "name": result.get("name"),
                "category": result.get("category"),
                "passed": bool(result.get("passed")),
                "score": float(result.get("score") or 0),
                "metrics": result.get("metrics") or {},
                "issues": result.get("issues") or [],
                "observed": result.get("observed") or {},
                "created_at": run["created_at"],
            })
        if rows:
            client.table("evaluation_case_results").insert(rows).execute()
        return True, None
    except Exception as exc:
        return False, str(exc)


def run_evaluation_suite(
    actor_uid: str,
    *,
    mode: str = "policy",
    case_ids: list[str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    requested_mode = str(mode or "policy").lower()
    if requested_mode not in {"policy", "live"}:
        raise ValueError("Evaluation mode must be 'policy' or 'live'.")
    cases = _select_cases(case_ids)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    for case in cases:
        if requested_mode == "policy":
            results.append(evaluate_policy_case(case))
            continue
        context = dict(case.get("context") or {})
        memory = dict(case.get("memory") or {})
        result = orchestrator.process_farmer_request(
            str(case.get("question") or ""),
            context,
            actor_uid,
            history=[],
            memory=memory,
        )
        result.setdefault("response_language", context.get("language") or (case.get("expected") or {}).get("language") or "English")
        results.append(evaluate_live_result(case, result))

    summary = _aggregate(results)
    duration_ms = int(round((time.perf_counter() - started) * 1000))
    run = {
        "id": f"eval_{uuid4().hex[:12]}",
        "framework": _FRAMEWORK,
        "mode": requested_mode,
        "status": "passed" if summary["failed"] == 0 else "needs_review",
        "created_at": now_iso(),
        "duration_ms": duration_ms,
        "summary": summary,
        "results": results,
    }
    persisted = False
    persistence_error = None
    if persist:
        persisted, persistence_error = _persist_run(run, results, actor_uid)
    run["persisted"] = persisted
    run["persistence_error"] = persistence_error
    return run


def list_evaluation_runs(limit: int = 20) -> list[dict[str, Any]]:
    if not evaluation_database_ready():
        return []
    data = service_client().table("evaluation_runs").select("*").order("created_at", desc=True).limit(max(1, min(int(limit), 100))).execute().data or []
    return list(data) if isinstance(data, list) else []


def get_evaluation_run(run_id: str) -> dict[str, Any] | None:
    if not evaluation_database_ready():
        return None
    client = service_client()
    run_data = client.table("evaluation_runs").select("*").eq("id", run_id).limit(1).execute().data or []
    if not run_data:
        return None
    result_data = client.table("evaluation_case_results").select("*").eq("run_id", run_id).order("created_at").execute().data or []
    return {**run_data[0], "results": list(result_data) if isinstance(result_data, list) else []}
