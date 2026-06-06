#!/usr/bin/env python3
"""Partner text cues — social/grammar vs literacy drill (ADR-0049 / teaching plan Block 5)."""

from __future__ import annotations

from typing import Any

from casa.prisms.control.tick import ControlExtensions
from casa.prisms.tick.semantic_read import classify_query_intent, route_kb_read


def is_social_partner_cue(query: str) -> bool:
    return classify_query_intent(query) == "social"


def is_grammar_partner_cue(query: str) -> bool:
    return classify_query_intent(query) == "grammar"


def partner_cue_read(query: str, bundle: dict[str, Any] | None) -> Any:
    return route_kb_read(query, bundle)


def social_concept_for_cue(query: str, bundle: dict[str, Any] | None) -> str | None:
    read = partner_cue_read(query, bundle)
    for cid in read.concept_hints:
        s = str(cid)
        if s.startswith(("lang.word.", "ru.dialog.")):
            return s
    for claim, _score in read.kb_hits:
        cid = str(claim.get("concept_id") or "")
        if cid.startswith(("lang.word.", "ru.dialog.")):
            return cid
    return None


def skip_hippo_surprise_for_partner_cue(query: str, bundle: dict[str, Any] | None) -> bool:
    """Social greeting with KB/lexical target — dialogue tract, not grapheme hippo."""
    if not is_social_partner_cue(query):
        return False
    return social_concept_for_cue(query, bundle) is not None


def skip_deliberate_practice_for_cue(query: str) -> bool:
    return is_social_partner_cue(query) or is_grammar_partner_cue(query)


def adjust_control_for_partner_cue(
    query: str,
    control: ControlExtensions,
    *,
    bundle: dict[str, Any] | None = None,
) -> ControlExtensions:
    """Remap grapheme fan-out surprise on «Привет» → lexical/dialog concept."""
    if not (query or "").strip():
        return control
    if not is_social_partner_cue(query):
        return control

    social_cid = social_concept_for_cue(query, bundle)
    if not social_cid:
        return control

    filtered = tuple(
        c
        for c in control.surprise
        if not str(c).startswith(("grapheme.", "syllable."))
    )
    if not filtered:
        filtered = (social_cid,)

    low_value = 0.12 if filtered == (social_cid,) else min(float(control.value), 0.22)
    return ControlExtensions(
        predicted=control.predicted,
        surprise=filtered,
        prediction_error=min(float(control.prediction_error), 0.12),
        dan_mask=control.dan_mask,
        sparse_ratio=control.sparse_ratio,
        masked_digest=control.masked_digest,
        value=low_value,
    )


def prepare_wm_for_partner_cue(wm: Any, query: str) -> None:
    """Partner turn: don't stay in grapheme practice WM."""
    if not is_social_partner_cue(query):
        return
    gid = str(getattr(wm, "goal_id", "") or "")
    if gid.startswith("goal.practice.") or gid.startswith("goal.revise.grapheme"):
        wm.goal_id = "goal.dialog.partner"
        wm.goal = f"dialogue:{query.strip()[:80]}"
        wm.subgoal = "social_reply"
        wm.step_capability = ""
        wm.step_focus = ""
        wm.plan_steps = []
        wm.step_index = 0
    if getattr(wm, "mode", "") in ("kb_query", ""):
        wm.mode = "dialogue"


def resolve_primary_surprise_concept(
    control: ControlExtensions,
    *,
    user_query: str | None = None,
    bundle: dict[str, Any] | None = None,
) -> str | None:
    if user_query:
        sc = social_concept_for_cue(user_query, bundle)
        if sc and is_social_partner_cue(user_query):
            return sc
    for cid in control.surprise:
        s = str(cid).strip()
        if s.startswith(("lang.", "ru.dialog.", "math.", "skill.", "vis.")):
            return s
    for cid in control.surprise:
        s = str(cid).strip()
        if not s.startswith(("grapheme.", "syllable.")):
            return s
    return str(control.surprise[0]).strip() if control.surprise else None
