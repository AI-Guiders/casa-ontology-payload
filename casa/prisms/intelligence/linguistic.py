#!/usr/bin/env python3
"""Linguistic Intelligence Zone — WM + discourse path (ADR-0061 P9)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root, zone_proportion_scale
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-linguistic-core"
SANDBOX_LATTICE = "agent-linguistic-sandbox"
CORE_PREFIX = "agent.linguistic."


def ensure_linguistic_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("linguistic", {})
    zone.setdefault("discourse_confidence", 0.5)
    zone.setdefault("phrase_pressure", 0.0)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    return zone


def spawn_linguistic_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_linguistic_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix="agent.linguistic.lab.",
    )
    if cfg.get("initial_discourse_confidence") is not None:
        zone["discourse_confidence"] = float(cfg["initial_discourse_confidence"])
    return rep


def linguistic_after_turn(
    state: dict,
    *,
    subject_reply: str,
    concept_hints: list[str] | None = None,
) -> dict[str, Any]:
    zone = ensure_linguistic_zone(state)
    has_lang = any(
        str(h).startswith(("lang.word.", "ru.dialog.", "percept.text", "ru.grammar."))
        for h in (concept_hints or [])
    )
    if has_lang and (subject_reply or "").strip():
        zone["discourse_confidence"] = min(1.0, float(zone["discourse_confidence"]) + 0.04)
        zone["phrase_pressure"] = max(0.0, float(zone.get("phrase_pressure") or 0.0) - 0.05)
    elif has_lang and not (subject_reply or "").strip():
        zone["phrase_pressure"] = min(1.0, float(zone.get("phrase_pressure") or 0.0) + 0.08)
    return {
        "discourse_confidence": float(zone["discourse_confidence"]),
        "phrase_pressure": float(zone["phrase_pressure"]),
    }


def linguistic_tract_boosts(state: dict, *, concept_hints: list[str] | None = None) -> dict[str, int]:
    zone = ensure_linguistic_zone(state)
    hints = concept_hints or []
    has_lang = any(str(h).startswith(("lang.word.", "ru.dialog.", "percept.")) for h in hints)
    if not has_lang:
        return {}
    conf = float(zone.get("discourse_confidence") or 0.5)
    scale = zone_proportion_scale(state, "linguistic", 1.0)
    boost = int((10 + 8 * conf) * scale)
    return {"general": boost // 2, "social": boost}


def linguistic_compose_deltas(state: dict, *, concept_hints: list[str] | None = None) -> dict[str, int]:
    zone = ensure_linguistic_zone(state)
    hints = concept_hints or []
    if not any(str(h).startswith(("lang.word.", "ru.dialog.", "percept.")) for h in hints):
        return {}
    conf = float(zone.get("discourse_confidence") or 0.5)
    return {
        "ru.dialog.greeting": int(8 * conf),
        "ru.dialog.self": int(6 * conf),
        "ru.dialog.affect": int(5 * conf),
    }
