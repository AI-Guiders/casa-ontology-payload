#!/usr/bin/env python3
"""Syllable segmentation hypotheses — guess, verify, apply learned rules."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import unicodedata
from typing import Any, Callable

RU_VOWELS = frozenset("аеёиоуыэюя")

SegmentFn = Callable[[str], list[str]]


def norm_word(word: str) -> str:
    return unicodedata.normalize("NFC", (word or "").strip().lower())


def vowel_count(word: str) -> int:
    w = norm_word(word)
    return sum(1 for c in w if c in RU_VOWELS)


def segment_vowel_nuclei(word: str) -> list[str]:
    """Correct rule: one vowel per syllable; onset consonants stay with their vowel."""
    w = norm_word(word)
    if not w:
        return []
    out: list[str] = []
    buf = ""
    for ch in w:
        buf += ch
        if ch in RU_VOWELS:
            out.append(buf)
            buf = ""
    if buf and out:
        out[-1] += buf
    elif buf:
        out.append(buf)
    return out


def segment_isolated_onset_guess(word: str) -> list[str]:
    """
    Pre-learning intuition (often wrong): long cluster before first vowel →
    first consonant is its own syllable. встреча → в|стре|ча (3).
    """
    w = norm_word(word)
    v_idx = [i for i, c in enumerate(w) if c in RU_VOWELS]
    if len(v_idx) < 2:
        return segment_vowel_nuclei(w)
    i0 = v_idx[0]
    if i0 >= 2:
        parts = [w[0], w[1 : i0 + 1]]
        start = i0 + 1
        for j in range(1, len(v_idx)):
            vi = v_idx[j]
            parts.append(w[start : vi + 1])
            start = vi + 1
        if start < len(w):
            parts[-1] += w[start:]
        return parts
    return segment_vowel_nuclei(w)


RULES: dict[str, dict[str, Any]] = {
    "rule.segment.vowel_nuclei": {
        "title": "гласных столько же, сколько слогов",
        "hint": "каждый слог содержит одну гласную; согласные при своей гласной",
        "fn": segment_vowel_nuclei,
    },
    "rule.segment.isolated_onset_guess": {
        "title": "интуиция: первый согласный отдельно при длинном кластере",
        "hint": "эвристика до обучения",
        "fn": segment_isolated_onset_guess,
    },
}


def segment_with_rule(rule_id: str, word: str) -> list[str]:
    spec = RULES.get(rule_id)
    if not spec:
        return segment_isolated_onset_guess(word)
    fn = spec["fn"]
    assert callable(fn)
    return fn(word)


def active_segment_rule(state: dict) -> str:
    """Reads R: votes on cylinder; None if field has no rule tokens yet."""
    from casa.prisms.memory.field_decode import active_rule_from_field

    rid, _ = active_rule_from_field(state)
    return rid or ""


def segment_hypothesis(state: dict, word: str) -> dict[str, Any]:
    from casa.prisms.memory.field_intuition import segment_field_intuition

    return segment_field_intuition(state, word)


def verify_segment(hyp: dict) -> dict[str, Any]:
    checks = {
        "join_ok": bool(hyp.get("join_ok")),
        "count_matches_vowels": bool(hyp.get("count_matches_vowels")),
    }
    ok = all(checks.values())
    return {"ok": ok, "checks": checks}


def format_segment(syllables: list[str]) -> str:
    return "|".join(syllables)


def parse_segment(text: str) -> list[str]:
    return [p.strip() for p in text.split("|") if p.strip()]
