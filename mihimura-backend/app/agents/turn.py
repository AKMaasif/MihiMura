"""The per-request state every MihiMura agent receives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.router import RouteDecision
from app.services.language import normalize_language


@dataclass
class Turn:
    """One user message, with everything the agents are allowed to know about it.

    ``context`` is the trusted context resolved by the conversation service
    (current message > conversation memory > owned project > profile).
    ``supplied`` is the raw context sent by the web app (e.g. a sensor reading).
    """

    question: str
    context: dict[str, Any]
    route: RouteDecision
    history: list[dict[str, str]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    supplied: dict[str, Any] = field(default_factory=dict)

    @property
    def language(self) -> str:
        return normalize_language(self.context.get("language") or "English")

    @property
    def crop(self) -> str:
        return str(self.context.get("crop") or "")

    @property
    def location(self) -> str:
        return str(self.context.get("location") or "")

    @property
    def coordinates(self) -> tuple[float, float] | None:
        lat, lon = self.context.get("lat"), self.context.get("lon")
        try:
            return (float(lat), float(lon)) if lat is not None and lon is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def known_facts(self) -> dict[str, Any]:
        return dict(self.memory.get("known_facts") or {})

    def model_context(self) -> dict[str, Any]:
        """The compact context block shown to the model (no internal plumbing)."""
        keys = (
            "language", "crop", "stage", "variety", "season", "irrigation", "location", "district",
            "area_value", "area_unit", "planting_date", "context_scope",
        )
        return {k: self.context.get(k) for k in keys if self.context.get(k) not in (None, "", [])}

    def model_memory(self) -> dict[str, Any]:
        return {
            "known_facts": {
                k: v for k, v in self.known_facts.items()
                if k not in {"lat", "lon", "language_confidence", "detected_language", "location_source"}
            },
            "active_intent": self.memory.get("active_intent"),
            "summary": self.memory.get("summary"),
        }
