#!/usr/bin/env python3
"""Intelligence Zone tick updates after partner/subject turn (ADR-0061)."""

from __future__ import annotations

from typing import Any

from casa.prisms.affect import (
    affect_after_turn,
    core_affect_state,
    ensure_emotional_zone,
    infer_life_event_from_turn,
)
from casa.prisms.intelligence.apply import intelligence_snapshot
from casa.prisms.intelligence.character import character_after_turn
from casa.prisms.intelligence.executive import executive_after_turn
from casa.prisms.intelligence.logical import logical_after_turn
from casa.prisms.intelligence.social import social_after_turn


def process_intelligence_turn(
    state: dict,
    *,
    partner_text: str,
    subject_reply: str,
    query_intent: str = "",
    concept_hints: list[str] | None = None,
    disposition: str = "",
    tick: int = 0,
    prior_hints: list[str] | None = None,
) -> dict[str, Any]:
    ensure_emotional_zone(state)
    life = infer_life_event_from_turn(
        state,
        partner_text=partner_text,
        subject_reply=subject_reply,
        query_intent=query_intent,
        disposition=disposition,
    )
    if life:
        affect_after_turn(state, life, tick=tick)
    if life == "self_failure" and any(str(h).startswith("math.") for h in (concept_hints or [])):
        affect_after_turn(state, "prediction_error", tick=tick)

    executive_after_turn(
        state,
        query=partner_text,
        concept_hints=concept_hints,
        prior_digest=prior_hints,
    )
    affect = core_affect_state(state)
    repair = bool(affect.episodic.get("dialog.repair_pending"))
    social_rep = social_after_turn(
        state,
        partner_text=partner_text,
        subject_reply=subject_reply,
        repair_pending=repair,
    )
    logical_after_turn(
        state,
        concept_hints=concept_hints,
        subject_reply=subject_reply,
        query_intent=query_intent,
    )
    character_after_turn(
        state,
        emotional_axes=affect.axes.to_dict(),
        social_trust=float(social_rep.get("partner_trust") or 0.5),
    )
    snap = intelligence_snapshot(state)
    if life:
        snap["life_event"] = life
    return snap


def ensure_all_zones_from_manifest(state: dict, manifest: dict[str, Any], *, tick: int = 0) -> dict[str, Any]:
    from casa.prisms.intelligence.migrate import migrate_all_zones

    return migrate_all_zones(state, manifest, tick=tick, persist=False)
