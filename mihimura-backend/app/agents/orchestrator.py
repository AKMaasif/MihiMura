"""Orchestrator: routes each farmer message to the right workflow agent.

    message ─► Context loader ─► Intent Router ─┬─► Mode Guard        (forced mode mismatch)
                                                ├─► Simple Chat       (+ knowledge search)
                                                ├─► Full Report       (clarify / follow-up / ready)
                                                └─► Decision Support  (tools ─► model ─► safety)

The orchestrator itself holds no farming logic; it builds the ``Turn``, picks a
workflow, and stamps routing metadata and latency on the answer.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.context import load_farmer_context
from app.agents.contracts import finalize_response
from app.agents.router import RouteDecision, route_request
from app.agents.turn import Turn
from app.agents.workflows.chat import run_chat
from app.agents.workflows.decision import run_decision
from app.agents.workflows.mode_guard import mode_switch_response
from app.agents.workflows.report import run_report

WORKFLOWS = {
    "simple_chat": run_chat,
    "full_report": run_report,
    "decision_support": run_decision,
}


def apply_route(out: dict[str, Any], route: RouteDecision) -> dict[str, Any]:
    out["requested_mode"] = route.requested_mode
    out["detected_mode"] = route.detected_mode
    out["effective_mode"] = route.effective_mode
    out["detected_intent"] = route.intent
    out["mode_reason"] = route.reason
    out.setdefault("suggested_mode", None)
    return out


class OrchestratorAgent:
    def process_farmer_request(
        self,
        question: str,
        context: dict[str, Any],
        uid: str,
        *,
        history: list[dict[str, str]] | None = None,
        memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        route = route_request(
            question,
            str(context.get("interaction_mode") or "auto"),
            memory or {},
            allow_mode_mismatch=bool(context.get("allow_mode_mismatch")),
        )
        if route.should_switch:
            out = mode_switch_response(route, question)
        else:
            turn = Turn(
                question=question,
                context=load_farmer_context(uid, context),
                route=route,
                history=history or [],
                memory=memory or {},
                supplied=context,
            )
            out = apply_route(WORKFLOWS[route.effective_mode](turn), route)
        out = finalize_response(out)
        out["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return out


orchestrator = OrchestratorAgent()
