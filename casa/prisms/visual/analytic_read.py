"""Analytic read (R1): syllable chain + lexicon bind — probe/lab, not hot wake path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
from casa.prisms.visual.bridge_lex import lex_concept_votes, predict_lex_for_vis_cue

_DEFAULT_PILOT = (
    Path(__file__).resolve().parents[3]
    / "lessons"
    / "literacy-cards"
    / "data"
    / "literacy"
    / "analytic-segments-ru-pilot-v1.json"
)


def corpus_word_frame_id(slug: str, *, face: str = "sans") -> str:
    return f"word-{slug}-{face}"


def analytic_probe_frame_id(slug: str) -> str:
    """Novel frame for R1 probe — must not match ingested corpus/analytic-teach ids."""
    return f"analytic-probe-{slug}-sans"


def syllable_frame_id(surface: str, *, face: str = "sans") -> str:
    return f"syllable-{surface}-{face}"


def load_pilot_segments(path: Path | str | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else _DEFAULT_PILOT
    doc = json.loads(p.read_text(encoding="utf-8"))
    return list(doc.get("entries") or [])


def chain_surface(segments: list[str]) -> str:
    return "".join(segments)


def leaders_at_max(preds: list[tuple[str, int]]) -> tuple[int, list[str]]:
    if not preds:
        return 0, []
    top = max(s for _, s in preds)
    return top, [c for c, s in preds if s == top]


def chain_compose_score(chain: dict[str, Any]) -> int:
    """Min syllable vote along teacher chain (all segments must be know)."""
    if not chain.get("chain_know"):
        return 0
    scores = [int(s.get("top_score") or 0) for s in chain.get("segments") or []]
    return min(scores) if scores else 0


def r1_novel_bind(
    *,
    chain: dict[str, Any],
    corpus_word_hit: bool,
    word_cid: str,
    novel_preds: list[tuple[str, int]],
    novel_metrics: dict[str, Any] | None,
    min_syllable_votes: int = 2,
    min_lum_ink_cells: int = 1,
) -> tuple[bool, str | None, int]:
    """Novel frame R1: direct lang.word on probe, or compose from chain + imprint ink."""
    _, novel_leaders = leaders_at_max(novel_preds)
    if word_cid in novel_leaders and len(novel_leaders) == 1:
        return True, "novel_whole", novel_preds[0][1] if novel_preds else 0

    ink = int((novel_metrics or {}).get("lum_ink_cells") or 0)
    compose_score = chain_compose_score(chain)
    if (
        chain.get("chain_know")
        and chain.get("surface_match")
        and corpus_word_hit
        and ink >= min_lum_ink_cells
        and compose_score >= min_syllable_votes
    ):
        return True, "novel_compose", compose_score
    return False, None, compose_score


def syllable_chain_status(
    state: dict,
    entry: dict[str, Any],
    *,
    min_votes: int = 2,
    predict: Any = predict_lex_for_vis_cue,
) -> dict[str, Any]:
    """Per-segment predict on trained syllable frame_ids (stage-05)."""
    rows: list[dict[str, Any]] = []
    all_know = True
    for surf, cid in zip(
        entry.get("syllables") or [],
        entry.get("syllable_concept_ids") or [],
        strict=True,
    ):
        fid = syllable_frame_id(str(surf))
        preds = predict(state, fid, top_k=5)
        hint = canonical_lex_concept_id(str(cid))
        top_score, leaders = leaders_at_max(preds)
        verdict = "empty"
        if leaders:
            if len(leaders) > 1:
                verdict = "ambiguous"
            elif leaders[0] == hint and top_score >= min_votes:
                verdict = "know"
            else:
                verdict = "wrong"
        if verdict != "know":
            all_know = False
        rows.append(
            {
                "syllable": surf,
                "frame_id": fid,
                "teacher_hint": hint,
                "verdict": verdict,
                "top_score": top_score,
                "leaders": leaders,
                "lex_top": [{"concept_id": c, "score": s} for c, s in preds],
            }
        )
    return {
        "chain_know": all_know,
        "joined_surface": chain_surface([str(s) for s in entry.get("syllables") or []]),
        "expected_surface": str(entry.get("surface") or ""),
        "surface_match": chain_surface([str(s) for s in entry.get("syllables") or []])
        == str(entry.get("surface") or ""),
        "segments": rows,
    }


def compose_analytic_read(
    state: dict,
    entry: dict[str, Any],
    *,
    novel_preds: list[tuple[str, int]] | None = None,
    novel_metrics: dict[str, Any] | None = None,
    min_syllable_votes: int = 2,
    min_lex_votes: int = 2,
    min_lum_ink_cells: int = 1,
    predict: Any = predict_lex_for_vis_cue,
) -> dict[str, Any]:
    """R1: corpus chain + optional novel bind (bridge or compose)."""
    slug = str(entry.get("slug") or "")
    surface = str(entry.get("surface") or "")
    word_cid = canonical_lex_concept_id(f"lang.word.{slug}")
    chain = syllable_chain_status(
        state, entry, min_votes=min_syllable_votes, predict=predict
    )
    lex_votes = lex_concept_votes(state, word_cid, min_votes=1)
    corpus_fid = corpus_word_frame_id(slug)
    corpus_preds = predict(state, corpus_fid, top_k=5)
    corpus_top_score, corpus_leaders = leaders_at_max(corpus_preds)
    corpus_word_hit = word_cid in corpus_leaders and corpus_top_score >= min_lex_votes
    lex_in_ltm = corpus_word_hit or lex_votes >= min_lex_votes

    novel_fid = analytic_probe_frame_id(slug)
    if novel_preds is None:
        novel_preds = predict(state, novel_fid, top_k=8)

    novel_top_score, novel_leaders = leaders_at_max(novel_preds)
    novel_word_hit = word_cid in novel_leaders
    grapheme_syllable = [
        {"concept_id": c, "score": s}
        for c, s in novel_preds
        if c.startswith("grapheme.") or c.startswith("syllable.")
    ]
    compose_score = chain_compose_score(chain)
    r1_novel, r1_novel_via, _compose_used = r1_novel_bind(
        chain=chain,
        corpus_word_hit=corpus_word_hit,
        word_cid=word_cid,
        novel_preds=novel_preds,
        novel_metrics=novel_metrics,
        min_syllable_votes=min_syllable_votes,
        min_lum_ink_cells=min_lum_ink_cells,
    )

    via: str | None = None
    verdict = "empty"
    if not chain["chain_know"]:
        verdict = "chain_incomplete"
    elif not chain["surface_match"]:
        verdict = "segmentation_mismatch"
    elif not corpus_word_hit:
        verdict = "word_not_in_ltm"
    elif r1_novel:
        verdict = "analytic_know"
        via = r1_novel_via
    elif corpus_word_hit and chain["chain_know"]:
        verdict = "analytic_know"
        via = "chain_plus_corpus_bridge"
    elif novel_leaders:
        verdict = "wrong"
        via = "novel_other"
    else:
        verdict = "empty"

    return {
        "surface": surface,
        "slug": slug,
        "word_concept_id": word_cid,
        "probe_frame_id": novel_fid,
        "chain": chain,
        "lex_votes": lex_votes,
        "corpus_frame_id": corpus_fid,
        "corpus_lex_top": [{"concept_id": c, "score": s} for c, s in corpus_preds],
        "corpus_word_hit": corpus_word_hit,
        "lex_in_ltm": lex_in_ltm,
        "novel_frame_id": novel_fid,
        "novel_lex_top": [{"concept_id": c, "score": s} for c, s in novel_preds],
        "novel_top_score": novel_top_score,
        "novel_leaders": novel_leaders,
        "novel_word_hit": novel_word_hit,
        "r1_novel_bind": r1_novel,
        "r1_novel_via": r1_novel_via,
        "chain_compose_score": compose_score,
        "novel_lum_ink_cells": int((novel_metrics or {}).get("lum_ink_cells") or 0),
        "grapheme_syllable_top": grapheme_syllable[:5],
        "verdict": verdict,
        "via": via,
    }
