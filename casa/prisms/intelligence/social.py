#!/usr/bin/env python3
"""Social Intelligence Zone — partner trust, repair (ADR-0061 P2)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice

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
    core_lid = str(cfg.get("core_lattice_id") or CORE_LATTICE)
    sandbox_lid = str(cfg.get("sandbox_lattice_id") or SANDBOX_LATTICE)
    lats = agent_lattices(state)
    if core_lid not in lats:
        create_agent_lattice(state, core_lid, concept_prefix=str(cfg.get("concept_prefix_core") or CORE_PREFIX))
    if sandbox_lid not in lats:
        create_agent_lattice(
            state,
            sandbox_lid,
            concept_prefix=str(cfg.get("concept_prefix_sandbox") or SANDBOX_PREFIX),
        )
    if cfg.get("initial_trust") is not None:
        zone["partner_trust"] = float(cfg["initial_trust"])
    zone["core_lattice_id"] = core_lid
    zone["sandbox_lattice_id"] = sandbox_lid
    return {"core_lattice_id": core_lid, "sandbox_lattice_id": sandbox_lid}


def social_after_turn(
    state: dict,
    *,
    partner_text: str,
    subject_reply: str,
    repair_pending: bool = False,
) -> dict[str, Any]:
    zone = ensure_social_zone(state)
    pt = (partner_text or "").lower()
    if re.search(r"\b(спасибо|благодар)\b", pt):
        zone["partner_trust"] = min(1.0, float(zone["partner_trust"]) + 0.08)
    if repair_pending and (subject_reply or "").strip():
        zone["repair_open"] = max(0.0, float(zone["repair_open"]) - 0.5)
        zone["partner_trust"] = min(1.0, float(zone["partner_trust"]) + 0.05)
    elif repair_pending:
        zone["repair_open"] = 1.0
    return {
        "partner_trust": float(zone["partner_trust"]),
        "repair_open": float(zone["repair_open"]),
    }


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
