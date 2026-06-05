"""Analytic read (R1): syllabify + corpus align; stage-05 syllables optional."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
from casa.prisms.visual.bridge_lex import lex_concept_votes, predict_lex_for_vis_cue
from casa.prisms.visual.corpus_lexicon import analytic_entry_from_corpus
from casa.prisms.visual.syllabify_ru import normalize_surface, syllabify_ru, syllable_concept_ids
from casa.prisms.visual.vis_frames import (
    FrameKind,
    analytic_probe_frame_id,
    parse_frame_ref,
    slug_from_frame,
    syllable_frame_id,
    word_frame_id,
)


def slug_from_vis_frame(cue_or_frame_id: str) -> str | None:
    """Extract word slug from vis cue or bare frame id."""
    return slug_from_frame(cue_or_frame_id)


def _ensure_entry_syllables(entry: dict[str, Any]) -> dict[str, Any]:
    ent = dict(entry)
    surface = str(ent.get("surface") or "")
    if not ent.get("syllables") and surface:
        ent["syllables"] = syllabify_ru(surface)
    syl = [str(s) for s in (ent.get("syllables") or []) if s]
    ent["syllables"] = syl
    if syl and not ent.get("syllable_concept_ids"):
        ent["syllable_concept_ids"] = syllable_concept_ids(syl)
    return ent


def lookup_analytic_entry(_state: dict | None, slug: str) -> dict[str, Any] | None:
    """Runtime entry: corpus manifest + syllabify."""
    key = str(slug or "").strip()
    return analytic_entry_from_corpus(slug=key) if key else None


def verify_analytic_read_frame(
    state: dict,
    frame_id: str,
    *,
    min_syllable_votes: int = 2,
    min_lex_votes: int = 2,
    predict: Any = predict_lex_for_vis_cue,
) -> bool:
    """Runtime R1 check aligned with lab compose (not phrase-probe top-k only)."""
    ref = parse_frame_ref(frame_id)
    if ref is None:
        return False
    slug = ref.slug if ref.kind != FrameKind.UNKNOWN else None
    if not slug:
        return False
    entry = lookup_analytic_entry(state, slug)
    if entry:
        novel_preds = None
        if ref.kind in (FrameKind.PHRASE_PROBE, FrameKind.ANALYTIC_PROBE):
            novel_preds = predict(state, ref.frame_id, top_k=8)
        row = compose_analytic_read(
            state,
            entry,
            novel_preds=novel_preds,
            min_syllable_votes=min_syllable_votes,
            min_lex_votes=min_lex_votes,
            predict=predict,
        )
        return row.get("verdict") == "analytic_know"
    return False


def corpus_word_frame_id(slug: str, *, face: str = "sans") -> str:
    return word_frame_id(slug, face=face)


def chain_surface(segments: list[str]) -> str:
    return "".join(segments)


def leaders_at_max(preds: list[tuple[str, int]]) -> tuple[int, list[str]]:
    if not preds:
        return 0, []
    top = max(s for _, s in preds)
    return top, [c for c, s in preds if s == top]


def chain_compose_score(chain: dict[str, Any]) -> int:
    """Min syllable vote along chain (all segments know) — optional reinforcement."""
    if not chain.get("chain_know"):
        return 0
    scores = [int(s.get("top_score") or 0) for s in chain.get("segments") or []]
    return min(scores) if scores else 0


def r1_novel_bind(
    *,
    chain: dict[str, Any],
    corpus_word_hit: bool,
    lex_in_ltm: bool,
    word_cid: str,
    novel_preds: list[tuple[str, int]],
    novel_metrics: dict[str, Any] | None,
    min_syllable_votes: int = 2,
    min_lum_ink_cells: int = 1,
) -> tuple[bool, str | None, int]:
    """Novel frame: direct lex, corpus align (syllabify+corpus), or syllable compose."""
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

    if (
        chain.get("surface_match")
        and lex_in_ltm
        and corpus_word_hit
        and ink >= min_lum_ink_cells
    ):
        return True, "corpus_align", compose_score
    return False, None, compose_score


def syllable_chain_status(
    state: dict,
    entry: dict[str, Any],
    *,
    min_votes: int = 2,
    predict: Any = predict_lex_for_vis_cue,
) -> dict[str, Any]:
    """Optional stage-05 reinforcement per syllable (not required for corpus_align)."""
    rows: list[dict[str, Any]] = []
    all_know = True
    syls = [str(s) for s in entry.get("syllables") or []]
    cids = [str(c) for c in entry.get("syllable_concept_ids") or []]
    if len(cids) < len(syls):
        cids = cids + syllable_concept_ids(syls[len(cids) :])
    for surf, cid in zip(syls, cids, strict=False):
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
    joined = chain_surface(syls)
    expected = normalize_surface(str(entry.get("surface") or ""))
    return {
        "chain_know": all_know,
        "joined_surface": joined,
        "expected_surface": str(entry.get("surface") or ""),
        "surface_match": joined == expected,
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
    """R1: syllabify + corpus match; stage-05 chain optional reinforcement."""
    entry = _ensure_entry_syllables(entry)
    slug = str(entry.get("slug") or "")
    surface = str(entry.get("surface") or "")
    word_cid = canonical_lex_concept_id(f"lang.word.{slug}")
    chain = syllable_chain_status(
        state, entry, min_votes=min_syllable_votes, predict=predict
    )
    lex_votes = lex_concept_votes(state, word_cid, min_votes=1)
    corpus_fid = str(entry.get("corpus_frame_id") or corpus_word_frame_id(slug))
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
        lex_in_ltm=lex_in_ltm,
        word_cid=word_cid,
        novel_preds=novel_preds,
        novel_metrics=novel_metrics,
        min_syllable_votes=min_syllable_votes,
        min_lum_ink_cells=min_lum_ink_cells,
    )

    via: str | None = None
    verdict = "empty"
    if not chain["surface_match"]:
        verdict = "segmentation_mismatch"
    elif not lex_in_ltm:
        verdict = "word_not_in_ltm"
    elif r1_novel:
        verdict = "analytic_know"
        via = r1_novel_via
    elif corpus_word_hit and chain["chain_know"]:
        verdict = "analytic_know"
        via = "chain_plus_corpus_bridge"
    elif not chain["chain_know"] and not r1_novel:
        verdict = "chain_incomplete"
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
        "entry_source": entry.get("source"),
    }


__all__ = [
    "analytic_probe_frame_id",
    "compose_analytic_read",
    "corpus_word_frame_id",
    "leaders_at_max",
    "lookup_analytic_entry",
    "slug_from_vis_frame",
    "syllable_chain_status",
    "syllable_frame_id",
    "verify_analytic_read_frame",
]
