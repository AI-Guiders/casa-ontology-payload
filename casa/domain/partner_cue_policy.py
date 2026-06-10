#!/usr/bin/env python3
"""Partner cue hooks — social routing, surprise gating, WM nudges."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.tick.semantic_read import _concept_hints_from_surface


def social_concept_for_cue(query: str, bundle: dict[str, Any] | None) -> str | None:
    """Primary social/dialog concept for partner surface (KB + routing claims)."""
    for cid in _concept_hints_from_surface(query, bundle):
        if cid.startswith(("lang.word.", "ru.dialog.")):
            return cid
    return None


def _is_social_partner_cue(query: str, bundle: dict[str, Any] | None) -> bool:
    if social_concept_for_cue(query, bundle):
        return True
    from casa.prisms.tick.semantic_read import classify_query_intent

    if not query.strip():
        return False
    return classify_query_intent(query, bundle) == "social"


def skip_hippo_surprise_for_partner_cue(query: str, bundle: dict[str, Any] | None) -> bool:
    """Greetings and social turns should not spawn grapheme hippo episodes."""
    return _is_social_partner_cue(query, bundle)


def skip_deliberate_practice_for_cue(cue: str, bundle: dict[str, Any] | None = None) -> bool:
    """Partner small-talk is not deliberate-practice material."""
    return skip_hippo_surprise_for_partner_cue(cue, bundle)


def prepare_wm_for_partner_cue(wm: WorkingMemory, query: str) -> None:
    if query.strip():
        wm.user_query = query.strip()


def adjust_control_for_partner_cue(
    query: str,
    control: ControlExtensions,
    *,
    bundle: dict[str, Any] | None = None,
) -> ControlExtensions:
    """Strip grapheme-level surprise when partner speaks socially."""
    if not skip_hippo_surprise_for_partner_cue(query, bundle):
        return control
    filtered = tuple(c for c in control.surprise if not str(c).startswith("grapheme."))
    if filtered == control.surprise and control.value < 0.3:
        return control
    new_value = control.value
    if any(str(c).startswith("grapheme.") for c in control.surprise):
        new_value = min(control.value, 0.25)
    if not filtered:
        new_value = min(new_value, 0.2)
    return replace(control, surprise=filtered, value=new_value)


def resolve_primary_surprise_concept(
    control: ControlExtensions,
    *,
    user_query: str | None = None,
    bundle: dict[str, Any] | None = None,
) -> str | None:
    social = social_concept_for_cue(user_query or "", bundle)
    if social:
        return social
    for cid in control.surprise:
        s = str(cid).strip()
        if s and not s.startswith("grapheme."):
            return s
    return None
