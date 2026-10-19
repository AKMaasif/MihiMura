"""Specialist evidence agents used by Decision Support.

Each specialist wraps one data service and knows how to describe its own result
honestly in the agent trace. ``collect_evidence`` runs only the specialists the
tool plan selected; independent ones run in parallel. The model later reasons
over this evidence but never decides which sources were checked.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from app.agents.agronomy import retrieve_approved_knowledge
from app.agents.contracts import step
from app.agents.soil_water import calculate_water_budget
from app.agents.turn import Turn
from app.services.climate_history import get_nasa_power
from app.services.economics import estimate_cultivation_economics
from app.services.market_intelligence import get_market_options
from app.services.resource_planning import build_resource_plan
from app.services.tool_runtime import execute_tool
from app.services.weather import get_weather
from app.services.weather_decision import build_weather_decision_context

NO_COORDINATES = "Resolved coordinates are required for live data."


@dataclass
class Evidence:
    """Everything the specialists produced for one turn."""

    weather: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "live": False, "current": {}, "daily": {}})
    weather_decision: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "decision_usable": False, "risk_flags": []})
    climate: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "live": False, "period": {}, "parameters": {}})
    knowledge: dict[str, Any] = field(default_factory=lambda: {"documents": [], "retrieval": "not_requested"})
    water: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested"})
    market: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "channels": [], "price_feed": "not_requested"})
    economics: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "scenarios": []})
    resources: dict[str, Any] = field(default_factory=lambda: {"status": "not_requested", "equipment": [], "tools": []})
    runtime: dict[str, dict[str, Any]] = field(default_factory=dict)
    trace: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Specialist:
    key: str  # tool-plan key and Evidence attribute
    agent: str  # name shown in the agent trace
    run: Callable[[Turn, Evidence], dict[str, Any]]
    describe: Callable[[dict[str, Any]], str]
    needs_coordinates: bool = False
    # Extra check that the result is real evidence, not just a successful call.
    healthy: Callable[[dict[str, Any]], bool] = lambda _: True


def _econ_facts(turn: Turn) -> dict[str, Any]:
    return {**turn.known_facts, **{k: turn.context.get(k) for k in ("crop", "location") if turn.context.get(k)}}


def _run_weather(turn: Turn, _: Evidence) -> dict[str, Any]:
    lat, lon = turn.coordinates  # type: ignore[misc]
    return get_weather(lat, lon, 14)


def _run_climate(turn: Turn, _: Evidence) -> dict[str, Any]:
    lat, lon = turn.coordinates  # type: ignore[misc]
    return get_nasa_power(lat, lon, 30)


def _run_agronomy(turn: Turn, _: Evidence) -> dict[str, Any]:
    return retrieve_approved_knowledge(turn.crop, turn.question, language=turn.language, location=turn.location)


def _run_water(turn: Turn, evidence: Evidence) -> dict[str, Any]:
    sensor = {k: v for k, v in turn.supplied.items() if k == "soil_moisture"}
    return calculate_water_budget({**turn.context, **sensor}, evidence.weather)


def _run_market(turn: Turn, _: Evidence) -> dict[str, Any]:
    return get_market_options(turn.crop, turn.location)


def _run_economics(turn: Turn, _: Evidence) -> dict[str, Any]:
    return estimate_cultivation_economics(_econ_facts(turn))


def _run_resources(turn: Turn, _: Evidence) -> dict[str, Any]:
    return build_resource_plan(turn.crop or str(_econ_facts(turn).get("crop") or ""))


SPECIALISTS: dict[str, Specialist] = {
    s.key: s
    for s in (
        Specialist(
            "weather", "Micro-Climate Prediction", _run_weather,
            lambda d: f"Live forecast from {d.get('source', 'weather service')}" if d.get("live") else "Live weather unavailable; no current-condition claim allowed",
            needs_coordinates=True,
        ),
        Specialist(
            "climate", "Climate Baseline", _run_climate,
            lambda d: f"30-day baseline from {d.get('source', 'NASA POWER')}" if d.get("live") else "Climate baseline unavailable",
            needs_coordinates=True,
        ),
        Specialist(
            "agronomy", "Agronomy Knowledge", _run_agronomy,
            lambda d: (
                f"{len(d.get('documents') or [])} indexed excerpt(s) retrieved"
                if d.get("retrieval") == "hybrid_pgvector_fts"
                else f"No indexed match; {len(d.get('documents') or [])} official source link(s) only"
            ),
            healthy=lambda d: d.get("retrieval") == "hybrid_pgvector_fts" and bool(d.get("documents")),
        ),
        Specialist(
            "market", "Market Intelligence", _run_market,
            lambda d: f"{len(d.get('channels') or [])} selling channel(s); live price feed: {d.get('price_feed', 'unknown')}",
        ),
        Specialist(
            "economics", "Economics Engine", _run_economics,
            lambda d: f"{len(d.get('scenarios') or [])} planning scenario(s); status={d.get('status', 'unknown')}",
        ),
        Specialist(
            "resources", "Resource Planner", _run_resources,
            lambda d: f"{len(d.get('equipment') or [])} equipment and {len(d.get('tools') or [])} tool item(s)",
        ),
        Specialist(
            "water", "Soil & Water", _run_water,
            lambda d: f"Water-context proxy; 3-day forecast rain {d.get('forecast_rain_3d_mm', '?')} mm",
        ),
    )
}

# Water uses the weather result, so it runs after the parallel batch.
_SEQUENTIAL = ("water",)


def _execute(spec: Specialist, turn: Turn, evidence: Evidence) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if spec.needs_coordinates and turn.coordinates is None:
        data = {"source": "Location required", "status": "unavailable", "live": False, "error": NO_COORDINATES}
        return spec.key, data, {"name": spec.key, "status": "unavailable", "latency_ms": 0, "error": NO_COORDINATES}
    run = execute_tool(spec.key, spec.run, turn, evidence)
    runtime = {k: v for k, v in run.items() if k != "data"}
    return spec.key, run.get("data") or {"status": run.get("status", "unavailable")}, runtime


def collect_evidence(turn: Turn, selected: dict[str, bool]) -> Evidence:
    """Run the selected specialists and return their evidence with an honest trace."""
    evidence = Evidence()
    wanted = [k for k, spec in SPECIALISTS.items() if selected.get(k) and k not in _SEQUENTIAL]

    results: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    if len(wanted) > 1:
        with ThreadPoolExecutor(max_workers=len(wanted)) as pool:
            results = list(pool.map(lambda k: _execute(SPECIALISTS[k], turn, evidence), wanted))
    elif wanted:
        results = [_execute(SPECIALISTS[wanted[0]], turn, evidence)]

    for key in _SEQUENTIAL:
        if selected.get(key):
            # Apply the parallel results first so sequential specialists can use them.
            for done_key, data, _ in results:
                setattr(evidence, done_key, data)
            results.append(_execute(SPECIALISTS[key], turn, evidence))

    for key, data, runtime in results:
        setattr(evidence, key, data)
        evidence.runtime[key] = runtime
        spec = SPECIALISTS[key]
        ok = runtime.get("status") == "success" and spec.healthy(data)
        detail = spec.describe(data) if ok or data else ""
        if runtime.get("error"):
            detail = f"{detail} ({runtime['error']})" if detail else str(runtime["error"])
        evidence.trace.append(step(spec.agent, f"{detail} · {runtime.get('latency_ms', 0)} ms", "complete" if ok else "watch"))

    if selected.get("weather"):
        evidence.weather_decision = build_weather_decision_context(evidence.weather, turn.question)
    return evidence
