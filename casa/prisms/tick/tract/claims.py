#!/usr/bin/env python3
"""Tract competition KB / speech-act claim scoring."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.tract.model import TRACT_IDS, TractScore, _BOOTSTRAP_TRACT_CLAIMS


def _split_cues(slot_val: str) -> list[str]:
    return [c.strip().lower() for c in re.split(r"[|,;]", slot_val) if c.strip()]


def _tokenize(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE)
        if len(t) > 2
    }


def slot_cue_hit(query_lower: str, slots: dict[str, str]) -> int:
    """Public cue match score for routing claims (cue_substrings / cue_words)."""
    return _slot_cue_hit(query_lower, slots)


def _slot_cue_hit(query_lower: str, slots: dict[str, str]) -> int:
    score = 0
    raw_sub = slots.get("cue_substrings") or ""
    if raw_sub:
        for cue in (c.strip().lower() for c in raw_sub.split("|") if c.strip()):
            if cue in query_lower:
                score += 12
    for key in ("boost_cues", "cues"):
        raw = slots.get(key) or ""
        if not raw:
            continue
        score += sum(12 for cue in _split_cues(raw) if cue in query_lower)
    qt = _tokenize(query_lower)
    for key in ("cue_words",):
        raw = slots.get(key) or ""
        if not raw:
            continue
        for w in _split_cues(raw):
            if w in qt:
                score += 10
    return score


def _bundle_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not bundle:
        return list(_BOOTSTRAP_TRACT_CLAIMS)
    claims = list(bundle.get("claims") or [])
    if not any(str(c.get("concept_id") or "").startswith("ru.tract.") for c in claims):
        return claims + _BOOTSTRAP_TRACT_CLAIMS
    return claims


def _tract_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        c for c in _bundle_claims(bundle) if str(c.get("concept_id") or "").startswith("ru.tract.")
    ]


def _speech_act_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        c
        for c in _bundle_claims(bundle)
        if str(c.get("concept_id") or "").startswith("ru.speech_act.")
    ]


def _kb_hit_affinity(kb_hits: list[tuple[dict[str, Any], int]]) -> dict[str, int]:
    boosts: dict[str, int] = dict.fromkeys(TRACT_IDS, 0)
    for claim, hit_score in kb_hits[:6]:
        cid = str(claim.get("concept_id") or "")
        if cid.startswith("ru.grammar."):
            boosts["grammar"] += min(24, hit_score // 2 + 8)
        elif cid.startswith("ru.dialog.explain"):
            boosts["explain"] += 20
        elif cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.")):
            boosts["grammar"] += 16
        elif cid.startswith("ru.dialog."):
            boosts["social"] += min(16, hit_score // 2)
        elif cid.startswith("math."):
            boosts["math"] += min(20, hit_score // 2)
        elif cid.startswith("ru.tract."):
            tid = cid.rsplit(".", 1)[-1]
            if tid in boosts:
                boosts[tid] += 16
    return boosts


def _score_tract_claims(
    query_lower: str,
    geo: dict[str, bool],
    bundle: dict[str, Any] | None,
    scores: dict[str, TractScore],
) -> None:
    for claim in _tract_claims(bundle):
        cid = str(claim.get("concept_id") or "")
        tract_id = cid.rsplit(".", 1)[-1]
        if tract_id not in scores:
            continue
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        req = str(slots.get("requires_geometry") or "").strip()
        if req and not geo.get(req):
            continue
        deny = str(slots.get("deny_geometry") or "").strip()
        if deny and geo.get(deny):
            continue
        cue_score = _slot_cue_hit(query_lower, slots)
        if cue_score:
            scores[tract_id].score += cue_score
            scores[tract_id].sources.append(f"kb:{cid}")


def _score_speech_acts(
    query_lower: str,
    geo: dict[str, bool],
    bundle: dict[str, Any] | None,
    scores: dict[str, TractScore],
) -> None:
    for claim in _speech_act_claims(bundle):
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        target = str(slots.get("tract") or "").strip()
        if target not in scores:
            continue
        req = str(slots.get("requires_geometry") or "").strip()
        if req and not geo.get(req):
            continue
        cue_score = _slot_cue_hit(query_lower, slots)
        if cue_score:
            scores[target].score += cue_score + 8
            scores[target].sources.append(f"speech_act:{claim.get('concept_id')}")
