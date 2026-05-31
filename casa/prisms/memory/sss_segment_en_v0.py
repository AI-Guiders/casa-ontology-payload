#!/usr/bin/env python3
"""English syllable segmentation — guess, verify, vowel nuclei rule."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from sss_segment_v0 import format_segment, norm_word  # type: ignore

EN_VOWELS = frozenset("aeiou")


def is_en_vowel(ch: str, index: int, word: str) -> bool:
    """Treat y as vowel at word end or between consonants (simple heuristic)."""
    if ch in EN_VOWELS:
        return True
    if ch != "y":
        return False
    if index == 0:
        return False
    if index == len(word) - 1:
        return True
    prev = word[index - 1]
    nxt = word[index + 1]
    prev_cons = prev not in EN_VOWELS and prev != "y"
    nxt_cons = nxt not in EN_VOWELS and nxt != "y"
    return prev_cons and nxt_cons


def vowel_count_en(word: str) -> int:
    w = norm_word(word)
    return sum(1 for i, c in enumerate(w) if is_en_vowel(c, i, w))


def segment_en_vowel_nuclei(word: str) -> list[str]:
    """Correct rule: one vowel per syllable; onset consonants stay with their vowel."""
    w = norm_word(word)
    if not w:
        return []
    out: list[str] = []
    buf = ""
    for i, ch in enumerate(w):
        buf += ch
        if is_en_vowel(ch, i, w):
            out.append(buf)
            buf = ""
    if buf and out:
        out[-1] += buf
    elif buf:
        out.append(buf)
    return out


def segment_en_guess(word: str) -> list[str]:
    """
    Pre-learning intuition (often wrong): long cluster before first vowel →
    first consonant is its own syllable. street → s|tr|et (3).
    """
    w = norm_word(word)
    v_idx = [i for i, c in enumerate(w) if is_en_vowel(c, i, w)]
    if len(v_idx) < 2:
        return segment_en_vowel_nuclei(w)
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
    return segment_en_vowel_nuclei(w)


def verify_segment_en(hyp: dict) -> dict[str, Any]:
    checks = {
        "join_ok": bool(hyp.get("join_ok")),
        "count_matches_vowels": bool(hyp.get("count_matches_vowels")),
    }
    ok = all(checks.values())
    return {"ok": ok, "checks": checks}


def segment_en_hypothesis(word: str, *, rule: str = "vowel_nuclei") -> dict[str, Any]:
    w = norm_word(word)
    if rule == "guess":
        syllables = segment_en_guess(w)
        rule_id = "rule.segment.en.isolated_onset_guess"
    else:
        syllables = segment_en_vowel_nuclei(w)
        rule_id = "rule.segment.en.vowel_nuclei"
    join_ok = "".join(syllables) == w
    count_matches_vowels = bool(syllables) and len(syllables) == vowel_count_en(w)
    return {
        "word": w,
        "syllables": syllables,
        "hypothesis": format_segment(syllables),
        "rule_id": rule_id,
        "join_ok": join_ok,
        "count_matches_vowels": count_matches_vowels,
    }


__all__ = [
    "EN_VOWELS",
    "format_segment",
    "is_en_vowel",
    "norm_word",
    "segment_en_guess",
    "segment_en_hypothesis",
    "segment_en_vowel_nuclei",
    "verify_segment_en",
    "vowel_count_en",
]
