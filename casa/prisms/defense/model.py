#!/usr/bin/env python3
"""Defense zone models — sandbox rechannel experiments (ADR-0076 P20b)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RechannelExperiment:
    experiment_id: str
    tick: int
    threat_cues: list[str] = field(default_factory=list)
    proxy_prefixes: list[str] = field(default_factory=list)
    rechannel_domain: str = "math"
    rechannel_tract: str = "math"
    note: str = ""
    score: float = 0.0
    promoted: bool = False
    mechanism: str = "rechannel"
    lattice_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "tick": int(self.tick),
            "threat_cues": list(self.threat_cues),
            "proxy_prefixes": list(self.proxy_prefixes),
            "rechannel_domain": self.rechannel_domain,
            "rechannel_tract": self.rechannel_tract,
            "note": self.note,
            "score": round(float(self.score), 4),
            "promoted": bool(self.promoted),
            "mechanism": self.mechanism,
            "lattice_id": str(self.lattice_id or ""),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RechannelExperiment:
        return cls(
            experiment_id=str(raw.get("experiment_id") or raw.get("id") or ""),
            tick=int(raw.get("tick") or 0),
            threat_cues=[str(c) for c in (raw.get("threat_cues") or [])],
            proxy_prefixes=[str(p) for p in (raw.get("proxy_prefixes") or [])],
            rechannel_domain=str(raw.get("rechannel_domain") or "math"),
            rechannel_tract=str(raw.get("rechannel_tract") or "math"),
            note=str(raw.get("note") or ""),
            score=float(raw.get("score") or 0.0),
            promoted=bool(raw.get("promoted")),
            mechanism=str(raw.get("mechanism") or "rechannel"),
            lattice_id=str(raw.get("lattice_id") or ""),
        )
