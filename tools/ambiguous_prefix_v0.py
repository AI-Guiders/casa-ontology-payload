#!/usr/bin/env python3
"""Ambiguous prefix lab: co → cow | сова until disambiguation (child view)."""

from __future__ import annotations

from typing import Any, Literal

from grapheme_clusters_v0 import l2_basin  # type: ignore
from homoglyph_v0 import dual_script_readings  # type: ignore
from predictor_v0 import l2_prefix_candidates  # type: ignore

Commitment = Literal["ambiguous", "resolved", "unknown"]


def _filter_ranked_by_lang(state: dict, ranked: list[tuple[str, int]], lang: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for word, votes in ranked:
        basin = l2_basin(state, word).get("basin")
        if lang == "en" and basin == "en":
            out.append((word, votes))
        elif lang == "ru" and basin == "ru":
            out.append((word, votes))
    return out


def predict_ambiguous_prefix(
    state: dict,
    visual: str,
    *,
    top_k: int = 8,
) -> dict[str, Any]:
    """
    Visual stream (e.g. co) may be read as latn and/or cyrl homoglyphs.
    Returns parallel word branches — child has not committed to script yet.
    """
    readings = dual_script_readings(visual)
    branches: list[dict[str, Any]] = []

    for rd in readings:
        lang = str(rd["language"])
        gstr = str(rd["grapheme_string"])
        ranked = l2_prefix_candidates(state, gstr, top_k=top_k * 2)
        filtered = _filter_ranked_by_lang(state, ranked, lang)[:top_k]
        anchors = [{"word": w, "votes": v, "language": lang, "script": rd["script"]} for w, v in filtered]
        branches.append(
            {
                **rd,
                "ranked": filtered,
                "anchors": anchors,
                "hypothesis": filtered[0][0] if filtered else None,
            }
        )

    active = [b for b in branches if b.get("anchors")]
    langs = {b["language"] for b in active}
    commitment: Commitment = "unknown"
    if len(langs) >= 2:
        commitment = "ambiguous"
    elif len(langs) == 1:
        commitment = "resolved"
    elif len(readings) >= 2:
        commitment = "ambiguous"

    resolved_lang: str | None = None
    if commitment == "resolved" and len(active) == 1:
        resolved_lang = str(active[0].get("language"))

    dual_top: dict[str, str | None] = {}
    for b in branches:
        dual_top[str(b["language"])] = b.get("hypothesis")

    return {
        "schema_version": 1,
        "modality": "ambiguous_prefix",
        "cue": visual,
        "visual": visual,
        "readings": readings,
        "branches": branches,
        "commitment": commitment,
        "hypothesis_lang": resolved_lang,
        "dual_hypothesis": dual_top,
        "confidence": 0.5 if commitment == "ambiguous" else (0.85 if commitment == "resolved" else 0.0),
        "lattice_ids": ["L0_grapheme", "L2_word", "L2_en_word"],
        "provenance": {"engine": "homoglyph_dual_read"},
    }


def ambiguous_tick(
    state: dict,
    visual: str,
    *,
    expect_commitment: str | None = None,
    expect_lang: str | None = None,
    expect_en_in: list[str] | None = None,
    expect_ru_in: list[str] | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    pred = predict_ambiguous_prefix(state, visual, top_k=top_k)

    en_words = [
        a["word"]
        for b in pred.get("branches") or []
        if b.get("language") == "en"
        for a in b.get("anchors") or []
    ]
    ru_words = [
        a["word"]
        for b in pred.get("branches") or []
        if b.get("language") == "ru"
        for a in b.get("anchors") or []
    ]

    checks: list[dict[str, Any]] = []
    ok = True

    if expect_commitment is not None:
        c_ok = pred.get("commitment") == expect_commitment
        checks.append({"name": "commitment", "pass": c_ok, "detail": pred.get("commitment")})
        ok = ok and c_ok

    if expect_lang is not None:
        l_ok = pred.get("hypothesis_lang") == expect_lang
        checks.append({"name": "lang", "pass": l_ok, "detail": pred.get("hypothesis_lang")})
        ok = ok and l_ok

    if expect_en_in:
        found = set(expect_en_in) & set(en_words)
        e_ok = len(found) >= 1
        checks.append({"name": "en_branch", "pass": e_ok, "detail": {"found": sorted(found), "anchors": en_words[:8]}})
        ok = ok and e_ok

    if expect_ru_in:
        found = set(expect_ru_in) & set(ru_words)
        r_ok = len(found) >= 1
        checks.append({"name": "ru_branch", "pass": r_ok, "detail": {"found": sorted(found), "anchors": ru_words[:8]}})
        ok = ok and r_ok

    return {
        "schema_version": 1,
        "modality": "ambiguous_prefix",
        "visual": visual,
        "predict": pred,
        "critic": {"verdict": "pass" if ok else "fail", "ok": ok, "checks": checks},
        "verdict": "pass" if ok else "fail",
        "commitment": pred.get("commitment"),
        "dual_hypothesis": pred.get("dual_hypothesis"),
    }


def simulate_ambiguous_track(
    state: dict,
    steps: list[dict[str, Any]],
    *,
    top_k: int = 8,
) -> dict[str, Any]:
    """Letter-by-letter track with per-step expectations."""
    trace: list[dict[str, Any]] = []
    all_ok = True
    for step in steps:
        visual = str(step.get("visual") or "")
        tick = ambiguous_tick(
            state,
            visual,
            expect_commitment=step.get("expect_commitment"),
            expect_lang=step.get("expect_lang"),
            expect_en_in=step.get("expect_en_in"),
            expect_ru_in=step.get("expect_ru_in"),
            top_k=top_k,
        )
        tick["step_id"] = step.get("id")
        trace.append(tick)
        all_ok = all_ok and tick["verdict"] == "pass"
    return {
        "schema_version": 1,
        "steps": len(trace),
        "trace": trace,
        "passed": all_ok,
    }
