#!/usr/bin/env python3
"""Predictor v0 — explicit hypothesis from field (segment, schema, T9 prefix)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import math
from dataclasses import dataclass
from typing import Any

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_stack import decode_f0_lattice, analyze_f0_cue_ranking
from casa.prisms.shared.lattice_names_v1 import PHRASES
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.lexicon_shard import L2_CONCEPT_PREFIX, is_l2_word_lattice, lattice_digest_l2_network
from casa.prisms.memory.lexicon_field_oracle import lexicon_oracle_for_predict
from casa.prisms.memory.lexicon_usage_axes import T9Policy, filter_ranked_for_t9, lemma_axis
from casa.prisms.memory.segment import format_segment, norm_word, segment_hypothesis, verify_segment


@dataclass(frozen=True)
class T9Weights:
    """Ranking weights for T9 prefix candidates.

    Tuned on the RU DetCorpus + EN folk dev sets (BiT9 gate, 2026-05). Values are
    relative scores, not physical units. Override per call via
    ``predict_t9(..., weights=T9Weights(...))`` rather than editing literals.
    """

    vote: float = 10.0  # field-vote mass per L2 headword
    remaining_penalty: float = 25.0  # cost per grapheme still to type (shorter completion wins)
    length_penalty: float = 0.5  # mild bias against long words on ties
    ipm_bonus: float = 4.0  # scale on log1p(ipm) (DetCorpus instances-per-million)
    rank_bonus_base: float = 12.0  # ceiling of the frequency-rank fallback bonus
    rank_bonus_slope: float = 3.0  # log10(rank) decay of the rank fallback
    freq_min_prefix: int = 3  # apply frequency tie-break only from 3 graphemes (homoglyph-safe)


DEFAULT_T9_WEIGHTS = T9Weights()


def word_anchors_from_ranked(
    ranked: list[tuple[str, int]],
    *,
    cue: str = "",
) -> list[dict[str, Any]]:
    """Ranked L2 headwords → anchor records (primary predict output for T9)."""
    if not ranked:
        return []
    max_v = max(int(v) for _, v in ranked) or 1
    anchors: list[dict[str, Any]] = []
    for i, (word, votes) in enumerate(ranked):
        w = norm_word(word)
        anchors.append(
            {
                "token": f"W:{w}",
                "concept_id": f"{L2_CONCEPT_PREFIX}{w}",
                "word": w,
                "votes": int(votes),
                "activation": round(int(votes) / max_v, 3),
                "rank": i + 1,
            }
        )
    return anchors


def focus_from_anchors(cue: str, anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Single focused anchor when cue fully matches top candidate."""
    p = norm_word(cue)
    if not p or not anchors:
        return None
    top = anchors[0]
    if norm_word(str(top.get("word") or "")) == p:
        return dict(top)
    return None


def _confidence_from_ranked(ranked: list[tuple[str, Any]], *, top_k: int = 5) -> float:
    if not ranked:
        return 0.0
    top = float(ranked[0][1]) if ranked else 0.0
    rest = sum(float(x[1]) for x in ranked[1:top_k])
    return round(top / max(1.0, top + rest), 3)


def _freq_bonus(
    word: str,
    prefix: str,
    axes: dict[str, dict[str, Any]] | None,
    *,
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> float:
    """DetCorpus ipm/rank — ranking tie-break from N+ grapheme prefix (homoglyph-safe)."""
    p = norm_word(prefix)
    if len(p) < weights.freq_min_prefix or not axes:
        return 0.0
    ax = lemma_axis(axes, word)
    if not ax:
        return 0.0
    ipm = float(ax.get("ipm") or 0)
    if ipm > 0:
        return math.log1p(ipm) * weights.ipm_bonus
    rank = int(ax.get("rank") or 0)
    if rank > 0:
        return max(0.0, weights.rank_bonus_base - math.log10(rank + 1) * weights.rank_bonus_slope)
    return 0.0


def _t9_score(
    word: str,
    votes: int,
    prefix: str,
    *,
    axes: dict[str, dict[str, Any]] | None = None,
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> float:
    """Field votes + length bias + lexicon ipm/rank (prefix ≥ weights.freq_min_prefix)."""
    w, p = norm_word(word), norm_word(prefix)
    if not w.startswith(p):
        return float("-inf")
    remaining = len(w) - len(p)
    return (
        float(votes) * weights.vote
        - remaining * weights.remaining_penalty
        - len(w) * weights.length_penalty
        + _freq_bonus(w, p, axes, weights=weights)
    )


def _prefix_bucket_key(prefix: str) -> str:
    p = norm_word(prefix)
    if not p:
        return ""
    return p[:2] if len(p) >= 2 else p[:1]


def build_l2_prefix_index(digest: list[tuple[str, int]]) -> dict[str, list[tuple[str, int]]]:
    """Bucket headwords by first 1–2 graphemes for O(bucket) prefix lookup."""
    index: dict[str, list[tuple[str, int]]] = {}
    for cid, votes in digest:
        if not cid.startswith(L2_CONCEPT_PREFIX):
            continue
        word = cid[len(L2_CONCEPT_PREFIX) :]
        if not word:
            continue
        key = word[:2] if len(word) >= 2 else word[:1]
        index.setdefault(key, []).append((word, int(votes)))
    return index


def _prefix_bucket_items(
    index: dict[str, list[tuple[str, int]]],
    prefix: str,
) -> list[tuple[str, int]]:
    p = norm_word(prefix)
    if not p:
        return []
    if len(p) >= 2:
        return index.get(_prefix_bucket_key(p), [])
    out: list[tuple[str, int]] = []
    for key, items in index.items():
        if key.startswith(p):
            out.extend(items)
    return out


def _prefix_from_index(
    index: dict[str, list[tuple[str, int]]],
    prefix: str,
    *,
    top_k: int = 8,
    axes: dict[str, dict[str, Any]] | None = None,
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> list[tuple[str, int]]:
    p = norm_word(prefix)
    if not p:
        return []
    bucket = _prefix_bucket_items(index, p)
    out = [(word, votes) for word, votes in bucket if word.startswith(p)]
    out.sort(key=lambda x: (-_t9_score(x[0], x[1], p, axes=axes, weights=weights), len(x[0]), x[0]))
    return out[:top_k]


def _prefix_from_digest(
    merged: list[tuple[str, int]],
    prefix: str,
    *,
    top_k: int = 8,
    axes: dict[str, dict[str, Any]] | None = None,
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> list[tuple[str, int]]:
    p = norm_word(prefix)
    if not p:
        return []
    out: list[tuple[str, int]] = []
    for cid, votes in merged:
        if not cid.startswith(L2_CONCEPT_PREFIX):
            continue
        word = cid[len(L2_CONCEPT_PREFIX) :]
        if word.startswith(p):
            out.append((word, int(votes)))
    out.sort(key=lambda x: (-_t9_score(x[0], x[1], p, axes=axes, weights=weights), len(x[0]), x[0]))
    return out[:top_k]


_L2_PREFIX_INDEX_CACHE = "__predictor_l2_prefix_index_v0__"


def l2_lexicon_digest(state: dict) -> list[tuple[str, int]]:
    """Full L2 concept digest — cache this for batch prefix sweeps."""
    return lattice_digest_l2_network(state)


def l2_prefix_index(state: dict, *, force: bool = False) -> dict[str, list[tuple[str, int]]]:
    """Prefix bucket index; built once per state and reused on hot path."""
    state = ensure_prisms(state)
    if not force and _L2_PREFIX_INDEX_CACHE in state:
        return state[_L2_PREFIX_INDEX_CACHE]
    index = build_l2_prefix_index(l2_lexicon_digest(state))
    state[_L2_PREFIX_INDEX_CACHE] = index
    return index


def l2_prefix_candidates(
    state: dict,
    prefix: str,
    *,
    top_k: int = 8,
    t9_policy: T9Policy = "prod",
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> list[tuple[str, int]]:
    """Words from L2 network matching prefix — field-only (T9)."""
    axes = lexicon_oracle_for_predict(state)
    raw = _prefix_from_index(
        l2_prefix_index(state),
        prefix,
        top_k=max(top_k * 4, 32),
        axes=axes or None,
        weights=weights,
    )
    return filter_ranked_for_t9(raw, axes, policy=t9_policy, top_k=top_k)


def l2_has_word(state: dict, word: str) -> bool:
    """True if exact headword is present on L2 (field-only)."""
    w = norm_word(word)
    if not w:
        return False
    ranked = l2_prefix_candidates(state, w, top_k=16)
    return any(norm_word(head) == w for head, _ in ranked)


def detect_lexicon_miss(prefix: str, ranked: list[tuple[str, int]]) -> dict[str, Any]:
    """T9 miss signal: non-empty prefix with zero L2 completions (cold-path queue v0)."""
    p = norm_word(prefix)
    if not p:
        return {"miss": False, "reason": None, "prefix": p}
    if not ranked:
        return {"miss": True, "reason": "no_prefix_matches", "prefix": p}
    return {"miss": False, "reason": None, "prefix": p}


def predict_segment(state: dict, cue: str) -> dict[str, Any]:
    state = ensure_prisms(state)
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
        "lattice_ids": ["syllables-ru", PHRASES],
        "nca_used": [],
        "provenance": {"engine": "segment_hypothesis"},
        "ranked": [(hypothesis, int(fs))],
    }


def schema_anchors_from_ranked(ranked: list[tuple[str, int]]) -> list[dict[str, Any]]:
    if not ranked:
        return []
    max_s = max(int(s) for _, s in ranked) or 1
    anchors: list[dict[str, Any]] = []
    for i, (concept_id, score) in enumerate(ranked):
        cid = str(concept_id)
        anchors.append(
            {
                "token": f"C:{cid}",
                "concept_id": cid,
                "votes": int(score),
                "activation": round(int(score) / max_s, 3),
                "rank": i + 1,
            }
        )
    return anchors


def focus_schema_from_anchors(cue: str, anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not anchors:
        return None
    if len(anchors) == 1:
        return dict(anchors[0])
    top = anchors[0]
    second = anchors[1]
    if int(top.get("votes") or 0) > int(second.get("votes") or 0):
        return dict(top)
    return None


def predict_schema(
    state: dict,
    cue: str,
    bundle: dict | None = None,
    *,
    lattice_id: str = "schema-math",
    top_k: int = 8,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    if lattice_id not in lattices:
        if bundle is None:
            raise ValueError(
                f"schema lattice {lattice_id!r} missing — boot store from ltm/ or run ingest (bundle optional bootstrap only)"
            )
        ingest_math_bundle(state, bundle, lattice_id=lattice_id)
        lattices = memory_lattices(state)
    decoded = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    analysis = analyze_f0_cue_ranking(decoded, cue, bundle=bundle)
    ranked = analysis["ranked"][:top_k]
    unbound = analysis.get("unbound_operators") or []
    anchors = schema_anchors_from_ranked(ranked)
    focus = focus_schema_from_anchors(cue, anchors)
    top = ranked[0][0] if ranked else None
    if unbound:
        top = None
        focus = None
    return {
        "schema_version": 1,
        "modality": "schema",
        "cue": cue,
        "anchors": anchors,
        "focus": focus,
        "hypothesis": top,
        "hypothesis_tokens": [top] if top else [],
        "unbound_operators": unbound,
        "coverage_gaps": analysis.get("coverage_gaps") or [],
        "digest": {
            "concept_ids": decoded.get("concept_ids") or [],
            "math_tokens": decoded.get("math_tokens") or [],
            "reading_contexts": analysis.get("contexts") or {},
        },
        "confidence": 0.0 if unbound else _confidence_from_ranked(ranked),
        "lattice_ids": [lattice_id],
        "nca_used": [],
        "provenance": {"engine": "analyze_f0_cue_ranking"},
        "ranked": ranked,
    }


def predict_t9(
    state: dict,
    cue: str,
    *,
    top_k: int = 8,
    t9_policy: T9Policy = "prod",
    weights: T9Weights = DEFAULT_T9_WEIGHTS,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    prefix = norm_word(cue)
    ranked = l2_prefix_candidates(state, prefix, top_k=top_k, t9_policy=t9_policy, weights=weights)
    axes = lexicon_oracle_for_predict(state)
    anchors = word_anchors_from_ranked(ranked, cue=prefix)
    focus = focus_from_anchors(prefix, anchors)
    top = ranked[0][0] if ranked else None
    lexicon_miss = detect_lexicon_miss(prefix, ranked)
    top_axis = lemma_axis(axes, top) if top and axes else None
    return {
        "schema_version": 1,
        "modality": "t9",
        "cue": prefix,
        "anchors": anchors,
        "focus": focus,
        "hypothesis": top,
        "hypothesis_tokens": [w for w, _ in ranked],
        "digest": {"prefix": prefix, "match_count": len(ranked)},
        "confidence": _confidence_from_ranked(ranked),
        "lexicon_miss": lexicon_miss,
        "lattice_ids": [lid for lid in memory_lattices(state) if is_l2_word_lattice(lid)],
        "nca_used": [],
        "provenance": {"engine": "l2_prefix_index_votes", "t9_policy": t9_policy},
        "lexicon_filter": {
            "policy": t9_policy,
            "axes_loaded": bool(axes),
            "top_lemma_axis": top_axis,
        },
        "ranked": ranked,
    }


def predict(
    state: dict,
    cue: str,
    *,
    modality: str,
    bundle: dict | None = None,
    lattice_id: str | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    """Returns Prediction dict; read-mostly (no sleep side effects).

    NCA repair is a sleep/offline path (see ``nca_repair``), not part of
    the read-only predict hot path.
    """
    mod = (modality or "segment").strip().lower()
    if mod in ("t9", "prefix_word", "prefix"):
        return predict_t9(state, cue, top_k=top_k)
    if mod == "script":
        from casa.prisms.memory.script_detect import predict_script

        return predict_script(state, cue)
    if mod == "schema":
        return predict_schema(state, cue, bundle, lattice_id=lattice_id or "schema-math")
    if mod == "segment":
        return predict_segment(state, cue)
    raise ValueError(f"unsupported modality: {modality}")
