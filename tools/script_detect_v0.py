#!/usr/bin/env python3
"""Infer script/language letter-by-letter from L0 grapheme basins (ADR-0003)."""

from __future__ import annotations

from typing import Any, Literal

from grapheme_clusters_v0 import _grapheme_concept_map  # type: ignore
from grapheme_ingest_v0 import GRAPHEME_CYRL_PREFIX, GRAPHEME_LATN_PREFIX  # type: ignore

Script = Literal["latn", "cyrl"]
Lang = Literal["en", "ru", "mixed", "unknown"]

SCRIPT_TO_LANG: dict[Script, Lang] = {"latn": "en", "cyrl": "ru"}


def _is_cyrillic(ch: str) -> bool:
    return len(ch) == 1 and "\u0400" <= ch <= "\u04ff"


def _is_latn_letter(ch: str) -> bool:
    return len(ch) == 1 and ("a" <= ch.lower() <= "z")


def _lookup_keys(ch: str) -> list[str]:
    keys: list[str] = []
    if _is_latn_letter(ch):
        keys.append(ch.lower())
    if _is_cyrillic(ch):
        keys.append(ch.lower())
    if ch not in keys:
        keys.append(ch)
    out: list[str] = []
    for k in keys:
        if k and k not in out:
            out.append(k)
    return out


def classify_char_l0(state: dict, ch: str) -> dict[str, Any]:
    """Map one character to L0 basin (latn/cyrl) using field only."""
    if len(ch) != 1 or ch in "-_'":
        return {"char": ch, "script": None, "concept_id": None, "votes": 0, "on_field": False}

    gmap = _grapheme_concept_map(state)
    best: tuple[Script, str, int] | None = None
    for key in _lookup_keys(ch):
        votes, cid = gmap.get(key, (0, ""))
        if not cid:
            continue
        script: Script | None = None
        if cid.startswith(GRAPHEME_LATN_PREFIX):
            script = "latn"
        elif cid.startswith(GRAPHEME_CYRL_PREFIX):
            script = "cyrl"
        if script and (best is None or votes > best[2]):
            best = (script, cid, votes)

    if best is None:
        return {"char": ch, "script": None, "concept_id": None, "votes": 0, "on_field": False}
    script, cid, votes = best
    return {
        "char": ch,
        "script": script,
        "concept_id": cid,
        "votes": votes,
        "on_field": True,
    }


def detect_script(state: dict, text: str) -> dict[str, Any]:
    """Aggregate script votes for text; dominant script from L0 letter hits."""
    latn_votes = 0
    cyrl_votes = 0
    latn_chars = 0
    cyrl_chars = 0
    unknown_chars = 0
    per_char: list[dict[str, Any]] = []

    for ch in text:
        if len(ch) != 1 or ch in "-_'":
            continue
        row = classify_char_l0(state, ch)
        per_char.append(row)
        script = row.get("script")
        votes = int(row.get("votes") or 0)
        if script == "latn":
            latn_votes += max(1, votes)
            latn_chars += 1
        elif script == "cyrl":
            cyrl_votes += max(1, votes)
            cyrl_chars += 1
        else:
            unknown_chars += 1

    dominant: Script | None = None
    if latn_votes > cyrl_votes:
        dominant = "latn"
    elif cyrl_votes > latn_votes:
        dominant = "cyrl"
    elif latn_votes and latn_votes == cyrl_votes:
        dominant = None

    return {
        "text": text,
        "latn_votes": latn_votes,
        "cyrl_votes": cyrl_votes,
        "latn_chars": latn_chars,
        "cyrl_chars": cyrl_chars,
        "unknown_chars": unknown_chars,
        "letter_count": latn_chars + cyrl_chars + unknown_chars,
        "dominant_script": dominant,
        "per_char": per_char,
    }


def infer_language(state: dict, text: str) -> dict[str, Any]:
    """Map L0 script basin → bilingual lang id (en/ru/mixed/unknown)."""
    det = detect_script(state, text)
    dom = det.get("dominant_script")
    latn_c = int(det.get("latn_chars") or 0)
    cyrl_c = int(det.get("cyrl_chars") or 0)
    unk = int(det.get("unknown_chars") or 0)

    lang: Lang = "unknown"
    if latn_c and cyrl_c:
        lang = "mixed"
    elif dom == "latn":
        lang = "en"
    elif dom == "cyrl":
        lang = "ru"
    elif latn_c == 0 and cyrl_c == 0 and unk == 0:
        lang = "unknown"

    conf = 0.0
    total = int(det.get("latn_votes") or 0) + int(det.get("cyrl_votes") or 0)
    if total and dom == "latn":
        conf = det["latn_votes"] / total
    elif total and dom == "cyrl":
        conf = det["cyrl_votes"] / total

    return {
        **det,
        "language": lang,
        "confidence": round(conf, 3),
    }


def predict_script(state: dict, prefix: str) -> dict[str, Any]:
    """Predict modality for growing prefix (letter-by-letter language id)."""
    inf = infer_language(state, prefix)
    lang = inf.get("language")
    script = inf.get("dominant_script")
    anchors: list[dict[str, Any]] = []
    if script:
        anchors.append(
            {
                "token": f"S:{script}",
                "concept_id": f"script.{script}",
                "script": script,
                "language": SCRIPT_TO_LANG.get(script),  # type: ignore[arg-type]
                "votes": int(inf.get("latn_votes" if script == "latn" else "cyrl_votes") or 0),
                "rank": 1,
            }
        )
    if lang in ("en", "ru"):
        anchors.append(
            {
                "token": f"L:{lang}",
                "concept_id": f"lang.{lang}",
                "language": lang,
                "script": script,
                "votes": int(inf.get("latn_votes" if lang == "en" else "cyrl_votes") or 0),
                "rank": 1 if len(anchors) == 0 else 2,
            }
        )

    return {
        "schema_version": 1,
        "modality": "script",
        "cue": prefix,
        "hypothesis": lang,
        "hypothesis_script": script,
        "hypothesis_lang": lang,
        "digest": {
            "latn_votes": inf.get("latn_votes"),
            "cyrl_votes": inf.get("cyrl_votes"),
            "letter_count": inf.get("letter_count"),
            "per_char": inf.get("per_char"),
        },
        "confidence": float(inf.get("confidence") or 0.0),
        "anchors": anchors,
        "lattice_ids": ["L0_grapheme"],
        "nca_used": [],
        "provenance": {"engine": "l0_grapheme_basin"},
    }
