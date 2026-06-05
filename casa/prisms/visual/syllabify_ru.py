#!/usr/bin/env python3
"""Russian syllabification v0 — rule tract (ADR-0032 A2), no teacher sidecar."""

from __future__ import annotations

import unicodedata

_VOWELS = frozenset("аеёиоуыэюя")


def normalize_surface(surface: str) -> str:
    return unicodedata.normalize("NFC", str(surface or "").strip().lower())


def syllabify_ru(surface: str) -> list[str]:
    """Split surface into Cyrillic syllables (one vowel nucleus each).

    Consonant cluster between vowels: one coda + rest as next onset (v0).
    """
    word = normalize_surface(surface)
    if not word:
        return []
    vowel_idx = [i for i, ch in enumerate(word) if ch in _VOWELS]
    if not vowel_idx:
        return [word]

    syllables: list[str] = []
    start = 0
    for vi, pos in enumerate(vowel_idx):
        if vi + 1 < len(vowel_idx):
            next_v = vowel_idx[vi + 1]
            mid = word[pos + 1 : next_v]
            if not mid:
                end = pos + 1
            elif len(mid) == 1:
                end = pos + 1
            else:
                end = pos + 2
        else:
            end = len(word)
        syllables.append(word[start:end])
        start = end
    if start < len(word):
        if syllables:
            syllables[-1] += word[start:]
        else:
            syllables.append(word[start:])
    return [s for s in syllables if s]


def syllable_concept_ids(syllables: list[str]) -> list[str]:
    return [f"syllable.{s}" for s in syllables if s]
