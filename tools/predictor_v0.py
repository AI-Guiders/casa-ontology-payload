#!/usr/bin/env python3
"""Predictor v0 — explicit hypothesis from field (segment, schema, T9 prefix)."""

from __future__ import annotations

from typing import Any

from f0_math_ingest_v0 import ingest_math_bundle  # type: ignore
from f0_stack_v0 import decode_f0_lattice, rank_cue_on_f0  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from sss_l2_shard_v0 import L2_CONCEPT_PREFIX, lattice_digest_l2_network  # type: ignore
from sss_segment_v0 import format_segment, norm_word, segment_hypothesis, verify_segment  # type: ignore


def _confidence_from_ranked(ranked: list[tuple[str, Any]], *, top_k: int = 5) -> float:
    if not ranked:
        return 0.0
    top = float(ranked[0][1]) if ranked else 0.0
    rest = sum(float(x[1]) for x in ranked[1:top_k])
    return round(top / max(1.0, top + rest), 3)


def _t9_score(word: str, votes: int, prefix: str) -> float:
    """Shorter completions win over long inflected forms (T9 disambiguation)."""
    w, p = norm_word(word), norm_word(prefix)
    if not w.startswith(p):
        return float("-inf")
    remaining = len(w) - len(p)
    return float(votes) * 10.0 - remaining * 25.0 - len(w) * 0.5


def l2_prefix_candidates(state: dict, prefix: str, *, top_k: int = 8) -> list[tuple[str, int]]:
    """Words from L2 network matching prefix — field-only (T9)."""
    p = norm_word(prefix)
    if not p:
        return []
    merged: list[tuple[str, int]] = []
    for cid, votes in lattice_digest_l2_network(state):
        if not cid.startswith(L2_CONCEPT_PREFIX):
            continue
        word = cid[len(L2_CONCEPT_PREFIX) :]
        if word.startswith(p):
            merged.append((word, int(votes)))
    merged.sort(key=lambda x: (-_t9_score(x[0], x[1], p), len(x[0]), x[0]))
    return merged[:top_k]


def predict_segment(state: dict, cue: str) -> dict[str, Any]:
    state = ensure_cylinders(state)
    word = norm_word(cue)
    hyp = segment_hypothesis(state, word)
    syllables = list(hyp.get("syllables") or [])
    hypothesis = format_segment(syllables)
    ver = verify_segment(hyp)
    fs = float(hyp.get("field_score") or 0)
    conf = min(1.0, fs / max(1.0, fs + 10.0)) if fs > 0 else (0.85 if ver["ok"] else 0.35)
    return {
        "schema_version": 1,
        "modality": "segment",
        "cue": word,
        "hypothesis": hypothesis,
        "hypothesis_tokens": syllables,
        "digest": {
            "active_rules": [hyp.get("rule_id")] if hyp.get("rule_id") else [],
            "segment_source": hyp.get("segment_source"),
            "verify": ver,
        },
        "confidence": round(conf, 3),
        "lattice_ids": ["L1_syllable", "L3_phrase"],
        "nca_used": [],
        "provenance": {"engine": "segment_hypothesis"},
        "ranked": [(hypothesis, int(fs))],
    }


def predict_schema(
    state: dict,
    cue: str,
    bundle: dict,
    *,
    lattice_id: str = "F0_schema",
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    lattices = memory_lattices(state)
    if lattice_id not in lattices:
        ingest_math_bundle(state, bundle, lattice_id=lattice_id)
        lattices = memory_lattices(state)
    decoded = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    ranked = rank_cue_on_f0(bundle, decoded, cue)
    top = ranked[0][0] if ranked else None
    top_score = ranked[0][1] if ranked else 0
    return {
        "schema_version": 1,
        "modality": "schema",
        "cue": cue,
        "hypothesis": top,
        "hypothesis_tokens": [top] if top else [],
        "digest": {
            "concept_ids": decoded.get("concept_ids") or [],
            "math_tokens": decoded.get("math_tokens") or [],
        },
        "confidence": _confidence_from_ranked(ranked),
        "lattice_ids": [lattice_id],
        "nca_used": [],
        "provenance": {"engine": "rank_cue_on_f0"},
        "ranked": ranked[:8],
    }


def predict_t9(state: dict, cue: str, *, top_k: int = 8) -> dict[str, Any]:
    state = ensure_cylinders(state)
    prefix = norm_word(cue)
    ranked = l2_prefix_candidates(state, prefix, top_k=top_k)
    top = ranked[0][0] if ranked else None
    return {
        "schema_version": 1,
        "modality": "t9",
        "cue": prefix,
        "hypothesis": top,
        "hypothesis_tokens": [w for w, _ in ranked],
        "digest": {"prefix": prefix, "match_count": len(ranked)},
        "confidence": _confidence_from_ranked(ranked),
        "lattice_ids": [lid for lid in memory_lattices(state) if lid.startswith("L2_word")],
        "nca_used": [],
        "provenance": {"engine": "l2_prefix_field_votes"},
        "ranked": ranked,
    }


def predict(
    state: dict,
    cue: str,
    *,
    modality: str,
    bundle: dict | None = None,
    lattice_id: str | None = None,
    nca_repair: bool = True,  # noqa: ARG001 — hook for v0.5+
    top_k: int = 8,
) -> dict[str, Any]:
    """Returns Prediction dict; read-mostly (no sleep side effects)."""
    mod = (modality or "segment").strip().lower()
    if mod in ("t9", "prefix_word", "prefix"):
        return predict_t9(state, cue, top_k=top_k)
    if mod == "schema":
        if bundle is None:
            raise ValueError("schema modality requires bundle")
        return predict_schema(state, cue, bundle, lattice_id=lattice_id or "F0_schema")
    if mod == "segment":
        return predict_segment(state, cue)
    raise ValueError(f"unsupported modality: {modality}")
