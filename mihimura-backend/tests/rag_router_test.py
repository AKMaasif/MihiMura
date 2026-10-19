"""Offline checks for RAG triggering in Simple Chat."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.workflows.chat import should_retrieve as _simple_chat_should_retrieve
from app.agents.router import route_request


def run() -> None:
    question = (
        "According to the indexed rice pest surveillance guidance, what observations should a field officer make "
        "when conducting pest surveillance in a rice field? Base your answer on the available source and tell me the document name."
    )
    route = route_request(question, "auto", {})
    assert route.detected_mode == "simple_chat"
    assert route.intent == "general_agriculture_question"
    assert _simple_chat_should_retrieve(route, question, {}) is True

    hello = route_request("hello", "auto", {})
    assert _simple_chat_should_retrieve(hello, "hello", {}) is False
    print("MihiMura RAG router regression test: PASS")


if __name__ == "__main__":
    run()
