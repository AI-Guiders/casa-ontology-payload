#!/usr/bin/env python3
"""Grapheme / L2 basin separability metrics (emergent tags bench, ADR-0003)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any, Literal

from casa.prisms.memory.grapheme_ingest_v0 import (
    GRAPHEME_CYRL_PREFIX,
    GRAPHEME_LATN_PREFIX,
    L0_CYRL_ID,
    L0_ID_LEGACY,
    L0_LATN_ID,
)
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_l2_shard_v0 import (
    L2_CONCEPT_PREFIX,
    concept_votes_l2,
    is_l2_en_word_lattice,
    is_l2_word_lattice,
    l2_word_lattice_ids,
)
from casa.prisms.memory.sss_stack_v0 import decode_lattice
from casa.prisms.memory.sss_vocab_v0 import norm_word

Basin = Literal["en", "ru", "latn", "cyrl"]


def _grapheme_concept_map(state: dict) -> dict[str, tuple[int, str]]:
    """char/suffix -> (votes, full concept_id) for all grapheme concepts on L0."""
    lattices = memory_lattices(ensure_prisms(state))
    out: dict[str, tuple[int, str]] = {}
    for lid in (L0_LATN_ID, L0_CYRL_ID, L0_ID_LEGACY):
        lat = lattices.get(lid) or {}
        if not lat.get("cells"):
            continue
        dec = decode_lattice(lat, min_votes=1)
        for c in dec.get("concepts") or []:
            cid = str(c.get("concept_id") or "")
            votes = int(c.get("votes") or 0)
            key: str | None = None
            if cid.startswith(GRAPHEME_LATN_PREFIX):
                key = cid[len(GRAPHEME_LATN_PREFIX) :]
            elif cid.startswith(GRAPHEME_CYRL_PREFIX):
                key = cid[len(GRAPHEME_CYRL_PREFIX) :]
            elif cid.startswith("grapheme.") and len(cid) > len("grapheme."):
                key = cid[len("grapheme.") :]
            if not key:
                continue
            prev = out.get(key)
            if prev is None or votes > prev[0]:
                out[key] = (votes, cid)
    return out


def l2_basin(state: dict, word: str) -> dict[str, Any]:
    """Which L2 namespace holds the lexeme (EN shard vs RU shard)."""
    w = norm_word(word)
    cid = f"{L2_CONCEPT_PREFIX}{w}"
    votes, lid = concept_votes_l2(state, cid)
    if votes <= 0:
        return {"word": w, "votes": 0, "lattice_id": lid, "basin": None}
    basin: Basin | None
    if lid and is_l2_en_word_lattice(str(lid)):
        basin = "en"
    elif lid and is_l2_word_lattice(str(lid)):
        basin = "ru"
    else:
        basin = None
    return {"word": w, "votes": votes, "lattice_id": lid, "basin": basin}


def l0_script_votes_for_word(state: dict, word: str) -> dict[str, Any]:
    """Per-letter script votes on L0 for letters in word."""
    w = norm_word(word) if word.isascii() else word.strip().lower()
    gmap = _grapheme_concept_map(state)
    latn = 0
    cyrl = 0
    per_char: list[dict[str, Any]] = []
    for ch in w:
        if ch in "-'":
            continue
        key = ch.lower()
        votes, cid = gmap.get(key, (0, ""))
        script: Basin | None = None
        if cid.startswith(GRAPHEME_LATN_PREFIX) or (len(key) == 1 and "a" <= key <= "z" and votes):
            script = "latn"
            latn += votes
        elif cid.startswith(GRAPHEME_CYRL_PREFIX) or (
            len(key) == 1 and "\u0400" <= key <= "\u04ff" and votes
        ):
            script = "cyrl"
            cyrl += votes
        per_char.append({"char": ch, "votes": votes, "concept_id": cid or None, "script": script})
    dominant: Basin | None = None
    if latn > cyrl:
        dominant = "latn"
    elif cyrl > latn:
        dominant = "cyrl"
    return {
        "word": w,
        "latn_votes": latn,
        "cyrl_votes": cyrl,
        "dominant_script": dominant,
        "per_char": per_char,
    }


def confusable_cross_talk(
    state: dict,
    word: str,
    *,
    expect_script: Basin,
    confusable_char: str,
) -> dict[str, Any]:
    """Votes for confusable glyph in the other script basin (B vs В)."""
    w = norm_word(word) if word.isascii() else word.strip().lower()
    gmap = _grapheme_concept_map(state)
    conf_key = confusable_char.lower()
    conf_votes, conf_cid = gmap.get(conf_key, (0, ""))
    own_votes = 0
    for ch in w:
        key = ch.lower()
        v, cid = gmap.get(key, (0, ""))
        if expect_script == "latn" and cid.startswith(GRAPHEME_LATN_PREFIX):
            own_votes += v
        elif expect_script == "cyrl" and (
            cid.startswith(GRAPHEME_CYRL_PREFIX)
            or (cid.startswith("grapheme.") and not cid.startswith(GRAPHEME_LATN_PREFIX))
        ):
            own_votes += v
        elif expect_script == "latn" and "a" <= key <= "z":
            own_votes += v
        elif expect_script == "cyrl" and "\u0400" <= key <= "\u04ff":
            own_votes += v
    cross_talk_ok = conf_votes == 0 or conf_votes < max(1, own_votes)
    return {
        "word": w,
        "expect_script": expect_script,
        "confusable_char": conf_key,
        "confusable_votes": conf_votes,
        "confusable_concept_id": conf_cid,
        "own_script_votes": own_votes,
        "cross_talk_ok": cross_talk_ok,
    }


def evaluate_cluster_cue(state: dict, item: dict) -> dict[str, Any]:
    cue = str(item.get("cue") or "")
    expect_l2 = str(item.get("expect_l2") or "")
    expect_l0 = str(item.get("expect_l0") or "")

    l2 = l2_basin(state, cue)
    l0 = l0_script_votes_for_word(state, cue)

    ok_l2 = (not expect_l2) or l2.get("basin") == expect_l2
    ok_l0 = (not expect_l0) or l0.get("dominant_script") == expect_l0
    ok = ok_l2 and ok_l0
    if expect_l2:
        ok = ok and int(l2.get("votes") or 0) > 0

    cross: dict[str, Any] | None = None
    conf = item.get("confusable_latn") or item.get("confusable_cyrl")
    if conf and expect_l0:
        cross = confusable_cross_talk(
            state,
            cue,
            expect_script=expect_l0,  # type: ignore[arg-type]
            confusable_char=str(conf),
        )
        ok = ok and cross.get("cross_talk_ok", False)

    return {
        "id": item.get("id"),
        "cue": cue,
        "expect_l2": expect_l2,
        "expect_l0": expect_l0,
        "l2": l2,
        "l0": l0,
        "cross_talk": cross,
        "ok": ok,
    }


def run_cluster_bench(state: dict, cues: list[dict]) -> dict[str, Any]:
    rows = [evaluate_cluster_cue(state, item) for item in cues]
    passed = sum(1 for r in rows if r.get("ok"))
    total = len(rows)
    return {
        "schema_version": 1,
        "bench": "grapheme_clusters_v0",
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "items": rows,
    }
