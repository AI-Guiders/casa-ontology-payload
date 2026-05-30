#!/usr/bin/env python3
"""Visual homoglyphs: one glyph stream, multiple script readings (ADR-0003 lab)."""

from __future__ import annotations

from typing import Any

# Latin → Cyrillic **homoglyphs** (visually the same glyph, two code points).
# NOT confusables: b≠в, n≠н, B≠В — separate basins / cross-talk bench only.
LATIN_TO_CYRL_HOMOGLYPH: dict[str, str] = {
    "a": "а",
    "c": "с",
    "e": "е",
    "o": "о",
    "p": "р",
    "x": "х",
    "y": "у",
}


def _is_cyrillic(ch: str) -> bool:
    return len(ch) == 1 and "\u0400" <= ch <= "\u04ff"


def _is_latn_letter(ch: str) -> bool:
    return len(ch) == 1 and ("a" <= ch.lower() <= "z")


def cyrl_homoglyph_reading(visual: str) -> str | None:
    """
    Map visual (often Latin typed) to Cyrillic string if every letter has
    a homoglyph or is already Cyrillic. Otherwise None — cyrl path dead.
    """
    out: list[str] = []
    for ch in visual:
        if len(ch) != 1:
            continue
        if _is_cyrillic(ch):
            out.append(ch.lower())
            continue
        low = ch.lower()
        if low in LATIN_TO_CYRL_HOMOGLYPH:
            out.append(LATIN_TO_CYRL_HOMOGLYPH[low])
            continue
        return None
    return "".join(out) if out else None


def latn_visual_reading(visual: str) -> str | None:
    """Keep visual as Latin if all letters are a-z."""
    out: list[str] = []
    for ch in visual:
        if len(ch) != 1:
            continue
        if _is_latn_letter(ch):
            out.append(ch.lower())
            continue
        if _is_cyrillic(ch):
            return None
        return None
    return "".join(out) if out else None


def dual_script_readings(visual: str) -> list[dict[str, Any]]:
    """All script readings still plausible for what the child sees."""
    readings: list[dict[str, Any]] = []
    latn = latn_visual_reading(visual)
    cyrl = cyrl_homoglyph_reading(visual)
    if latn:
        readings.append({"script": "latn", "grapheme_string": latn, "language": "en"})
    if cyrl and cyrl != latn:
        readings.append({"script": "cyrl", "grapheme_string": cyrl, "language": "ru"})
    elif cyrl and latn is None:
        readings.append({"script": "cyrl", "grapheme_string": cyrl, "language": "ru"})
    return readings
