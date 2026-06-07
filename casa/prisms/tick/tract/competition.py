#!/usr/bin/env python3
"""Tract competition argmax — intent = winning F-tract on field."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.passage.comprehend import passage_focus_question
from casa.prisms.tick.passage.meaning import extract_passage_meaning, proposition_tract_boost
from casa.prisms.tick.tract.claims import (
    _kb_hit_affinity,
    _score_speech_acts,
    _score_tract_claims,
)
from casa.prisms.tick.tract.geometry import _geometry_score_for_tract, geometry_signals
from casa.prisms.tick.tract.model import TRACT_IDS, TractScore


def compete_tract_intent(
    query: str,
    bundle: dict[str, Any] | None,
    *,
    kb_hits: list[tuple[dict[str, Any], int]] | None = None,
    store_dir: Any | None = None,
    state: dict[str, Any] | None = None,
) -> tuple[str, list[TractScore]]:
    """Argmax F-tract score → intent id."""
    raw = (query or "").strip()
    if not raw:
        return "general", [TractScore("general", 1, ["empty"])]

    ql = passage_focus_question(raw).lower()
    geo = geometry_signals(raw)
    scores: dict[str, TractScore] = {t: TractScore(t, 0) for t in TRACT_IDS}

    for tract_id in TRACT_IDS:
        g, gs = _geometry_score_for_tract(tract_id, geo)
        if g:
            scores[tract_id].score += g
            scores[tract_id].sources.extend(gs)

    _score_tract_claims(ql, geo, bundle, scores)
    _score_speech_acts(ql, geo, bundle, scores)

    prop_rows = extract_passage_meaning(raw, bundle=bundle, store_dir=store_dir)
    for tract_id, boost in proposition_tract_boost(
        prop_rows, store_dir=store_dir, query=raw
    ).items():
        if boost and tract_id in scores:
            scores[tract_id].score += boost
            scores[tract_id].sources.append("meaning:props")

    if kb_hits:
        for tract_id, boost in _kb_hit_affinity(kb_hits).items():
            if boost:
                scores[tract_id].score += boost
                scores[tract_id].sources.append("kb_affinity")

    if state is not None:
        from casa.prisms.memory.intent import intent_tract_boosts
        from casa.prisms.memory.wm import wm_tract_boosts

        for tract_id, boost in intent_tract_boosts(state, raw).items():
            if tract_id not in scores:
                scores[tract_id] = TractScore(tract_id, 0)
            if boost:
                scores[tract_id].score += boost
                scores[tract_id].sources.append("intent_prism")

        for tract_id, boost in wm_tract_boosts(state, raw).items():
            if boost and tract_id in scores:
                scores[tract_id].score += boost
                scores[tract_id].sources.append("wm_prism")

    ranked = sorted(scores.values(), key=lambda t: t.score, reverse=True)
    winner = ranked[0]
    if winner.score <= 0:
        return "general", ranked
    return winner.tract_id, ranked
