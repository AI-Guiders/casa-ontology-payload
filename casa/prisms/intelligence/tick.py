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
from casa.prisms.intelligence.linguistic import linguistic_after_turn
from casa.prisms.intelligence.logical import logical_after_turn
from casa.prisms.intelligence.social import social_after_turn


def intelligence_before_partner_compose(
    state: dict,
    *,
    partner_text: str,
    query_intent: str = "",
    disposition: str = "",
    tick: int = 0,
) -> dict[str, Any]:
    """Partner cues that must bias compose in the same turn (ADR-0061 tick order)."""
    from casa.prisms.affect import affect_after_turn, infer_partner_life_event

    ensure_emotional_zone(state)
    life = infer_partner_life_event(partner_text, query_intent=query_intent)
    if life:
        try:
            from casa.prisms.neuromodulator import neuromodulator_after_event, neuromodulator_is_active

            if neuromodulator_is_active(state):
                neuromodulator_after_event(state, life, tick=tick)
        except ImportError:
            pass
        affect_after_turn(state, life, tick=tick)
    if life == "partner_repair_invite":
        from casa.prisms.intelligence.social import ensure_social_zone

        ensure_social_zone(state)["repair_open"] = 1.0
    return {"life_event": life} if life else {}


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
        try:
            from casa.prisms.intelligence.executive import ensure_executive_zone
            from casa.prisms.neuromodulator import neuromodulator_after_event, neuromodulator_is_active

            surprise_n = 0
            if neuromodulator_is_active(state):
                if life == "self_failure" and any(str(h).startswith("math.") for h in (concept_hints or [])):
                    surprise_n = int(ensure_executive_zone(state).get("predict_surprise_n") or 0)
                neuromodulator_after_event(state, life, tick=tick, surprise_n=surprise_n)
        except ImportError:
            pass
        affect_after_turn(state, life, tick=tick)
    if life == "self_failure" and any(str(h).startswith("math.") for h in (concept_hints or [])):
        try:
            from casa.prisms.neuromodulator import neuromodulator_after_event, neuromodulator_is_active

            if neuromodulator_is_active(state):
                from casa.prisms.intelligence.executive import ensure_executive_zone

                surprise_n = int(ensure_executive_zone(state).get("predict_surprise_n") or 0)
                neuromodulator_after_event(state, "prediction_error", tick=tick, surprise_n=surprise_n)
        except ImportError:
            pass
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
    linguistic_after_turn(
        state,
        subject_reply=subject_reply,
        concept_hints=concept_hints,
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
