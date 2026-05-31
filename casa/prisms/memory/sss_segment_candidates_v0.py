#!/usr/bin/env python3
"""Segment candidates from field + signal only — no external canon."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_field_decode_v0 import (
    grapheme_votes_for_word,
    rule_votes_from_field,
    segment_lattice_greedy,
)
from casa.prisms.memory.sss_segment_v0 import RU_VOWELS, norm_word, vowel_count
from casa.prisms.memory.sss_stack_v0 import decode_lattice


def _syllable_vote_map(state: dict) -> dict[str, int]:
    l1 = memory_lattices(ensure_prisms(state)).get("L1_syllable") or {}
    dec = decode_lattice(l1, min_votes=1)
    out: dict[str, int] = {}
    for c in dec.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith("syllable."):
            out[cid[len("syllable.") :]] = int(c.get("votes") or 0)
    return out


def chunk_field_score(state: dict, chunk: str, *, gvotes: dict[str, int], syl_votes: dict[str, int]) -> float:
    if chunk in syl_votes:
        return float(syl_votes[chunk]) * (1.0 + 0.25 * len(chunk))
    return sum(float(gvotes.get(ch, 0)) for ch in chunk)


def score_candidate(
    state: dict,
    word: str,
    syllables: list[str],
    *,
    rule_votes: dict[str, int] | None = None,
) -> float:
    w = norm_word(word)
    if not syllables or "".join(syllables) != w:
        return float("-inf")
    gvotes = grapheme_votes_for_word(state, word)
    syl_votes = _syllable_vote_map(state)
    base = sum(chunk_field_score(state, s, gvotes=gvotes, syl_votes=syl_votes) for s in syllables)
    rule_votes = rule_votes if rule_votes is not None else rule_votes_from_field(state)
    if rule_votes.get("rule.segment.vowel_nuclei") and len(syllables) == vowel_count(w):
        base += float(rule_votes["rule.segment.vowel_nuclei"]) * 8.0
    return base


def segment_vowel_nuclei_from_signal(word: str) -> list[str]:
    """Read vowels in the stimulus — not KB lookup."""
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


def segment_isolated_onset_from_signal(word: str) -> list[str]:
    """Variant: strong first grapheme as its own chunk when cluster before first vowel is long."""
    w = norm_word(word)
    v_idx = [i for i, c in enumerate(w) if c in RU_VOWELS]
    if len(v_idx) < 2:
        return segment_vowel_nuclei_from_signal(w)
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
    return segment_vowel_nuclei_from_signal(w)


def enumerate_field_candidates(state: dict, word: str) -> list[dict[str, Any]]:
    """Competing cuts ranked by field score; agent never sees gold."""
    w = norm_word(word)
    rule_votes = rule_votes_from_field(state)
    seen: set[tuple[str, ...]] = set()
    raw: list[list[str]] = []

    def add(parts: list[str]) -> None:
        key = tuple(parts)
        if key not in seen and parts and "".join(parts) == w:
            seen.add(key)
            raw.append(parts)

    add(segment_vowel_nuclei_from_signal(w))
    add(segment_isolated_onset_from_signal(w))
    greedy = segment_lattice_greedy(state, w)
    if greedy:
        add(greedy)

    ranked: list[dict[str, Any]] = []
    for parts in raw:
        score = score_candidate(state, w, parts, rule_votes=rule_votes)
        ranked.append(
            {
                "syllables": parts,
                "field_score": round(score, 3),
                "syllable_count": len(parts),
                "vowel_count": vowel_count(w),
                "join_ok": True,
                "count_matches_vowels": len(parts) == vowel_count(w),
            }
        )
    ranked.sort(key=lambda x: (-float(x["field_score"]), x["syllables"]))
    return ranked


def pick_field_candidate(state: dict, word: str) -> dict[str, Any]:
    ranked = enumerate_field_candidates(state, word)
    if not ranked:
        w = norm_word(word)
        parts = [w] if w else []
        return {
            "syllables": parts,
            "field_score": 0.0,
            "syllable_count": len(parts),
            "vowel_count": vowel_count(w),
            "join_ok": True,
            "count_matches_vowels": len(parts) == vowel_count(w),
            "candidate_rank": 0,
            "candidates_considered": 0,
        }
    best = ranked[0]
    return {**best, "candidate_rank": 0, "candidates_considered": len(ranked), "alternatives": ranked[1:4]}
