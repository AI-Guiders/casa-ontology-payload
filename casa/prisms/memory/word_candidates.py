#!/usr/bin/env python3
"""Word surface candidates from stream chunk — field score + L1 compose verify."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.field_decode import grapheme_votes_for_word, segment_lattice_greedy, syllable_hits_from_field
from casa.prisms.memory.segment_candidates import score_candidate, segment_vowel_nuclei_from_signal
from casa.prisms.memory.segment import format_segment, norm_word


def _compose_score(state: dict, surface: str, syllables: list[str]) -> float:
    return score_candidate(state, surface, syllables)


def enumerate_word_candidates(state: dict, surface: str) -> list[dict[str, Any]]:
    """
    Competing word hypotheses for one stream chunk (space/punct bounded).
    Same surface may have multiple internal syllable parses — scored on field.
    """
    w = norm_word(surface)
    if not w:
        return []

    candidates: dict[str, dict[str, Any]] = {}
    gvotes = grapheme_votes_for_word(state, w)
    gscore = float(sum(gvotes.values()))

    def add(syllables: list[str], *, source: str) -> None:
        joined = "".join(syllables)
        if joined != w:
            return
        seg = format_segment(syllables)
        fs = _compose_score(state, w, syllables)
        candidates[seg] = {
            "surface": w,
            "syllables": syllables,
            "segment": seg,
            "field_score": fs,
            "grapheme_score": gscore,
            "source": source,
            "join_ok": True,
        }

    add([w], source="whole")
    vn = segment_vowel_nuclei_from_signal(w)
    if vn:
        add(vn, source="vowel_nuclei_signal")
    greedy = segment_lattice_greedy(state, w)
    if greedy:
        add(greedy, source="l1_greedy")
    for syl, _ in syllable_hits_from_field(state, w)[:6]:
        if syl == w:
            add([w], source="syllable_hit")

    if not candidates:
        return [
            {
                "surface": w,
                "syllables": [w],
                "segment": format_segment([w]),
                "field_score": gscore,
                "grapheme_score": gscore,
                "source": "fallback",
                "join_ok": False,
            }
        ]

    return sorted(candidates.values(), key=lambda c: (-c["field_score"], c["segment"]))
