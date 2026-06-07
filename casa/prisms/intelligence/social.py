#!/usr/bin/env python3
"""Social Intelligence Zone — partner trust, repair (ADR-0061 P2)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root, zone_proportion_scale
from casa.prisms.intelligence.partner_cues import apply_partner_trust_cue
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-social-core"
SANDBOX_LATTICE = "agent-social-sandbox"
CORE_PREFIX = "agent.social."
SANDBOX_PREFIX = "agent.social.lab."


def ensure_social_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("social", {})
    zone.setdefault("partner_trust", 0.5)
    zone.setdefault("repair_open", 0.0)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    zone.setdefault("sandbox", {"experiments": [], "next_experiment_id": 1})
    return zone


def spawn_social_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_social_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    if cfg.get("initial_trust") is not None:
        zone["partner_trust"] = float(cfg["initial_trust"])
    return rep


def social_after_turn(
    state: dict,
    *,
    partner_text: str,
    subject_reply: str,
    repair_pending: bool = False,
) -> dict[str, Any]:
    zone = ensure_social_zone(state)
    apply_partner_trust_cue(state, partner_text)
    if repair_pending and (subject_reply or "").strip():
        zone["repair_open"] = max(0.0, float(zone["repair_open"]) - 0.5)
        zone["partner_trust"] = min(1.0, float(zone["partner_trust"]) + 0.05)
    elif repair_pending:
        zone["repair_open"] = 1.0
    return {
        "partner_trust": float(zone["partner_trust"]),
        "repair_open": float(zone["repair_open"]),
    }


def social_tract_boosts(state: dict, *, concept_hints: list[str] | None = None) -> dict[str, int]:
    zone = ensure_social_zone(state)
    scale = zone_proportion_scale(state, "social", 1.0)
    trust = float(zone.get("partner_trust") or 0.5)
    repair = float(zone.get("repair_open") or 0.0)
    boosts: dict[str, int] = {}
    if trust > 0.55:
        boosts["social"] = int(6 + 10 * (trust - 0.5) * scale)
    if repair > 0:
        boosts["social"] = boosts.get("social", 0) + int(8 * scale)
        boosts["general"] = int(4 * scale)
    hints = concept_hints or []
    if any(str(h).startswith("ru.dialog.") for h in hints):
        boosts["social"] = boosts.get("social", 0) + int(4 * scale)
    return boosts


def social_compose_deltas(state: dict, *, repair_pending: bool) -> dict[str, int]:
    zone = ensure_social_zone(state)
    trust = float(zone.get("partner_trust") or 0.5)
    deltas: dict[str, int] = {}
    if repair_pending:
        deltas["subject.dialog.partner_recent"] = 20
        deltas["ru.dialog.capabilities"] = -28
        deltas["ru.dialog.affect"] = -12
    if trust > 0.6:
        deltas["ru.dialog.thanks"] = 6
    return deltas
