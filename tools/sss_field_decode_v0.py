#!/usr/bin/env python3
"""Decode field lattices — shared by intuition and candidates."""

from __future__ import annotations

from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_segment_v0 import norm_word  # type: ignore
from sss_stack_v0 import decode_lattice  # type: ignore


def _token_votes(lattice: dict, *, prefix: str) -> dict[str, int]:
    vote: dict[str, int] = {}
    for cell in lattice.get("cells") or []:
        for t in cell:
            if t.startswith(prefix):
                key = t[len(prefix) :]
                vote[key] = vote.get(key, 0) + 1
    return vote


def all_field_lattices(state: dict) -> dict[str, dict]:
    state = ensure_prisms(state)
    out = dict(memory_lattices(state))
    hippo = prism_hippo(state)
    for lid, lat in (hippo.get("lattices") or {}).items():
        out[f"hippo_{lid}"] = lat
    return out


def rule_votes_from_field(state: dict) -> dict[str, int]:
    votes: dict[str, int] = {}
    for lat in all_field_lattices(state).values():
        for rid, v in _token_votes(lat, prefix="R:").items():
            votes[rid] = votes.get(rid, 0) + v
    return votes


def active_rule_from_field(state: dict) -> tuple[str | None, dict[str, int]]:
    votes = rule_votes_from_field(state)
    if not votes:
        return None, votes
    rid = max(votes, key=lambda k: (votes[k], k))
    return rid, votes


def grapheme_votes_for_word(state: dict, word: str) -> dict[str, int]:
    lattices = memory_lattices(ensure_prisms(state))
    cmap: dict[str, int] = {}
    for lid in ("L0_grapheme_cyrl", "L0_grapheme_latn", "L0_grapheme"):
        lat = lattices.get(lid) or {}
        if not lat:
            continue
        dec = decode_lattice(lat, min_votes=1)
        for c in dec.get("concepts") or []:
            cid = str(c.get("concept_id") or "")
            if not cid.startswith("grapheme."):
                continue
            ch = cid.split(".", 2)[-1]
            cmap[ch] = cmap.get(ch, 0) + int(c.get("votes") or 0)
    w = norm_word(word)
    return {ch: cmap.get(ch, 0) for ch in w}


def syllable_hits_from_field(state: dict, word: str) -> list[tuple[str, int]]:
    lattices = memory_lattices(ensure_prisms(state))
    l1 = lattices.get("L1_syllable") or {}
    dec = decode_lattice(l1, min_votes=1)
    w = norm_word(word)
    hits: list[tuple[str, int]] = []
    for c in dec.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if not cid.startswith("syllable."):
            continue
        surf = cid[len("syllable.") :]
        if surf and surf in w:
            hits.append((surf, int(c.get("votes") or 0)))
    hits.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))
    return hits


def segment_lattice_greedy(state: dict, word: str) -> list[str] | None:
    w = norm_word(word)
    hits = syllable_hits_from_field(state, word)
    if not hits:
        return None
    parts: list[str] = []
    i = 0
    while i < len(w):
        match = None
        for surf, _ in hits:
            if w.startswith(surf, i):
                if match is None or len(surf) > len(match):
                    match = surf
        if not match:
            return None
        parts.append(match)
        i += len(match)
    return parts if parts and "".join(parts) == w else None
