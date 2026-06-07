#!/usr/bin/env python3
"""Emotional Zone model — core limbic axes + sandbox experiments (ADR-0060)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_CORE_LATTICE = "agent-limbic-core"
DEFAULT_SANDBOX_LATTICE = "agent-affect-sandbox"
CORE_PREFIX = "agent.limbic."
SANDBOX_PREFIX = "agent.affect.lab."

DEFAULT_AXES: dict[str, float] = {
    "valence": 0.0,
    "arousal": 0.2,
    "security": 0.5,
}

DEFAULT_ZONE_POLICY: dict[str, Any] = {
    "sandbox_writes_core": False,
    "promote_theta": 0.65,
    "max_sandbox_lattices": 2,
    "max_experiments": 32,
}

LIFE_EVENTS = frozenset(
    {
        "partner_greeting",
        "self_failure",
        "partner_repair_invite",
        "self_repair_success",
        "partner_trust",
        "prediction_error",
    }
)


@dataclass
class AffectAxes:
    valence: float = 0.0
    arousal: float = 0.2
    security: float = 0.5

    def clamped(self) -> AffectAxes:
        return AffectAxes(
            valence=max(-1.0, min(1.0, float(self.valence))),
            arousal=max(0.0, min(1.0, float(self.arousal))),
            security=max(0.0, min(1.0, float(self.security))),
        )

    def to_dict(self) -> dict[str, float]:
        c = self.clamped()
        return {"valence": c.valence, "arousal": c.arousal, "security": c.security}

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> AffectAxes:
        raw = raw or {}
        return cls(
            valence=float(raw.get("valence") or 0.0),
            arousal=float(raw.get("arousal") if raw.get("arousal") is not None else 0.2),
            security=float(raw.get("security") if raw.get("security") is not None else 0.5),
        )


@dataclass
class CoreAffectState:
    axes: AffectAxes = field(default_factory=AffectAxes)
    episodic: dict[str, float] = field(default_factory=dict)
    last_event: str = ""
    tick: int = 0
    lattice_id: str = DEFAULT_CORE_LATTICE

    def to_dict(self) -> dict[str, Any]:
        return {
            "axes": self.axes.to_dict(),
            "episodic": dict(self.episodic),
            "last_event": self.last_event,
            "tick": int(self.tick),
            "lattice_id": self.lattice_id,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> CoreAffectState:
        raw = raw or {}
        return cls(
            axes=AffectAxes.from_dict(raw.get("axes") if isinstance(raw.get("axes"), dict) else raw),
            episodic={str(k): float(v) for k, v in (raw.get("episodic") or {}).items()},
            last_event=str(raw.get("last_event") or ""),
            tick=int(raw.get("tick") or 0),
            lattice_id=str(raw.get("lattice_id") or DEFAULT_CORE_LATTICE),
        )


@dataclass
class SandboxExperiment:
    experiment_id: str
    tick: int
    deltas: dict[str, float]
    note: str = ""
    score: float = 0.0
    promoted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "tick": self.tick,
            "deltas": dict(self.deltas),
            "note": self.note,
            "score": round(float(self.score), 4),
            "promoted": bool(self.promoted),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SandboxExperiment:
        return cls(
            experiment_id=str(raw.get("experiment_id") or raw.get("id") or ""),
            tick=int(raw.get("tick") or 0),
            deltas={str(k): float(v) for k, v in (raw.get("deltas") or {}).items()},
            note=str(raw.get("note") or ""),
            score=float(raw.get("score") or 0.0),
            promoted=bool(raw.get("promoted")),
        )
