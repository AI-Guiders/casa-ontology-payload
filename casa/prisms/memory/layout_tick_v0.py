#!/usr/bin/env python3
"""Layout-parity tick: decode branches → unified_tick → argmax winner (ADR-0008 L2)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.tick.unified_tick_v0 import unified_tick
from casa.prisms.memory.vk_decode_v0 import decode_branches


def infer_segment(grapheme: str) -> str:
    g = grapheme or ""
    if g.startswith("/") or g.startswith("@"):
        return "command"
    cyr = sum(1 for c in g if "\u0400" <= c <= "\u04ff")
    latn = sum(1 for c in g if c.isascii() and c.isalpha())
    if cyr > latn and cyr > 0:
        return "prose"
    if latn > 0 and g[:1].isascii():
        return "command" if g.startswith("/") else "prose"
    return "prose"


def _top_activation(tick: dict[str, Any]) -> float:
    best = 0.0
    for tb in tick.get("t9_branches") or []:
        pred = tb.get("predict") or {}
        for a in pred.get("anchors") or []:
            best = max(best, float(a.get("activation") or 0.0))
    return best


def _branch_langs(tick: dict[str, Any]) -> set[str]:
    langs: set[str] = set()
    for tb in tick.get("t9_branches") or []:
        lang = tb.get("language")
        if lang:
            langs.add(str(lang))
    return langs


def _anchor_words(tick: dict[str, Any], *, lang: str | None = None) -> list[str]:
    out: list[str] = []
    for tb in tick.get("t9_branches") or []:
        if lang and tb.get("language") != lang:
            continue
        pred = tb.get("predict") or {}
        for a in pred.get("anchors") or []:
            w = a.get("word")
            if w:
                out.append(str(w))
    return out


def score_layout_branch(
    tick: dict[str, Any],
    *,
    layout_id: str,
    grapheme: str,
    segment: str,
) -> float:
    score = _top_activation(tick)
    langs = _branch_langs(tick)
    anchors_en = _anchor_words(tick, lang="en")
    anchors_ru = _anchor_words(tick, lang="ru")

    if segment == "command":
        if grapheme.startswith("/"):
            score += 2.0
        if "en" in langs:
            score += 1.0
        if layout_id == "qwerty_us":
            score += 1.5
        if any(w.startswith("attach") for w in anchors_en):
            score += 3.0
    elif segment == "prose":
        if any("\u0400" <= c <= "\u04ff" for c in grapheme):
            score += 1.5
        if "ru" in langs:
            score += 1.0
        if layout_id == "jcuken_ru":
            score += 1.0
        if anchors_ru:
            score += 0.5

    if tick.get("verdict") == "pass":
        score += 0.25
    return score


def t9_cue_for_segment(grapheme: str, segment: str) -> str:
    g = grapheme or ""
    if segment == "command" and len(g) > 1 and g[0] in "/@":
        return g[1:]
    return g


def layout_tick(
    state: dict,
    events: list[dict[str, Any]],
    *,
    layout_ids: list[str] | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    branches_text = decode_branches(events, layout_ids, state=state)
    segment = infer_segment(next(iter(branches_text.values()), ""))
    for g in branches_text.values():
        segment = infer_segment(g) if infer_segment(g) == "command" else segment

    branch_ticks: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    for layout_id, grapheme in branches_text.items():
        t9_cue = t9_cue_for_segment(grapheme, segment)
        tick = unified_tick(state, t9_cue, context=segment, top_k=top_k)
        branch_ticks[layout_id] = {
            "layout_id": layout_id,
            "grapheme_string": grapheme,
            "t9_cue": t9_cue,
            "segment": segment,
            "tick": tick,
            "anchors_en": _anchor_words(tick, lang="en"),
            "anchors_ru": _anchor_words(tick, lang="ru"),
        }
        scores[layout_id] = score_layout_branch(
            tick,
            layout_id=layout_id,
            grapheme=grapheme,
            segment=segment,
        )

    winner = max(scores, key=lambda k: scores[k]) if scores else None
    winner_row = branch_ticks.get(winner or "") or {}

    return {
        "schema_version": 1,
        "modality": "layout_parity",
        "segment": segment,
        "decode": branches_text,
        "branches": list(branch_ticks.values()),
        "scores": scores,
        "winner_layout": winner,
        "winner_grapheme": branches_text.get(winner or ""),
        "winner_anchors_en": winner_row.get("anchors_en") or [],
        "winner_anchors_ru": winner_row.get("anchors_ru") or [],
    }
