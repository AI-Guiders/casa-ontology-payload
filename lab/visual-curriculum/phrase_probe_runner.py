#!/usr/bin/env python3
"""Shared phrase probe loop — store R1 reads + compose verdict (agent KSA gate)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from font_legibility_lab import production_font_pt, restore_visual_cells, snapshot_visual_cells
from phrase_crop import crop_word_rgb, phrase_word_boxes, render_phrase_rgb


def normalize_word(word: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", word.strip()).lower()


def phrase_event_surfaces(entry: dict[str, Any]) -> list[str]:
    surfaces = list(entry.get("surfaces") or [])
    if surfaces:
        return [str(s).strip() for s in surfaces if str(s).strip()]
    words = entry.get("words") or []
    if words:
        return [" ".join(str(w.get("surface") or "") for w in words)]
    return []


def merge_phrase_event_example(entry: dict[str, Any], example: dict[str, Any]) -> dict[str, Any]:
    """Flat view for one lab illustration (possessive/numeral examples[])."""
    merged = dict(entry)
    for key in ("surfaces", "words", "gender_id", "lemma", "question_frames"):
        if key in example:
            merged[key] = example[key]
    if example.get("gender_id"):
        merged["example_gender_id"] = example["gender_id"]
    return merged


def phrase_event_probe_slices(entry: dict[str, Any]) -> list[tuple[dict[str, Any], int]]:
    """One held-out slice per event — flat words/surfaces, else first example."""
    if entry.get("words") and phrase_event_surfaces(entry):
        return [(entry, 0)]
    examples = entry.get("examples")
    if isinstance(examples, list) and examples:
        ex = next((x for x in examples if isinstance(x, dict)), None)
        if ex is None:
            return []
        merged = merge_phrase_event_example(entry, ex)
        if not phrase_event_surfaces(merged):
            return []
        return [(merged, 0)]
    if not phrase_event_surfaces(entry):
        return []
    return [(entry, 0)]


def read_phrase_on_store(
    state: dict[str, Any],
    *,
    event_entry: dict[str, Any],
    phrase: str,
    min_syllable_votes: int = 2,
    min_lex_votes: int = 2,
    font_pt: int = 0,
) -> dict[str, Any]:
    """Per-word analytic R1 on phrase crop; restore vis after each word."""
    from casa.prisms.visual.analytic_read import compose_analytic_read
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue
    from casa.prisms.visual.imprint import imprint_visual_frame
    from casa.prisms.visual.phrase_compose import (
        analytic_entry_from_word,
        compose_phrase_verdict,
        phrase_probe_frame_id,
    )
    from font_legibility_lab import lum_imprint_metrics

    vis_snap = snapshot_visual_cells(state)
    pt = int(font_pt) if int(font_pt) > 0 else int(production_font_pt(phrase))
    if len(phrase) > 18 and pt > 48:
        pt = 48
    phrase_rgb = render_phrase_rgb(phrase, pt)
    boxes = phrase_word_boxes(phrase, pt)
    box_by_word = {normalize_word(b["word"]): b for b in boxes}

    word_reads: list[dict[str, Any]] = []
    for spec in event_entry.get("words") or []:
        surface = str(spec.get("surface") or "")
        key = normalize_word(surface)
        box = box_by_word.get(key)
        if box is None:
            word_reads.append(
                {
                    "surface": surface,
                    "slug": spec.get("slug"),
                    "verdict": "word_missing_on_line",
                    "error": "surface not found in phrase render",
                }
            )
            continue

        crop_rgb = crop_word_rgb(phrase_rgb, list(box["bbox"]))
        fid = phrase_probe_frame_id(str(spec.get("slug") or ""))
        imprint_visual_frame(state, crop_rgb, frame_id=fid, record_episode=False)
        metrics = lum_imprint_metrics(crop_rgb)
        novel_preds = predict_lex_for_vis_cue(state, fid, top_k=8)

        analytic_ent = analytic_entry_from_word(spec)
        if analytic_ent is None:
            word_reads.append(
                {
                    "surface": spec.get("surface"),
                    "verdict": "word_not_in_corpus",
                    "phrase_frame_id": fid,
                }
            )
            continue

        row = compose_analytic_read(
            state,
            analytic_ent,
            novel_preds=novel_preds,
            novel_metrics=metrics,
            min_syllable_votes=min_syllable_votes,
            min_lex_votes=min_lex_votes,
            predict=predict_lex_for_vis_cue,
        )
        row["phrase_frame_id"] = fid
        row["bbox"] = box["bbox"]
        word_reads.append(row)
        restore_visual_cells(state, vis_snap)

    composed = compose_phrase_verdict(word_reads, event_entry)
    return {
        "phrase": phrase,
        "font_pt": pt,
        "verdict": composed["verdict"],
        "phrase_know": composed["phrase_know"],
        "slots": composed["slots"],
        "agreement": composed["agreement"],
        "word_reads": word_reads,
        "total_words": len(word_reads),
        "know_words": sum(1 for r in word_reads if r.get("verdict") == "analytic_know"),
    }


def run_phrase_cases_on_store(
    state: dict[str, Any],
    *,
    entries: Sequence[dict[str, Any]],
    event_ids: Sequence[str] | None = None,
    surface_indices: Sequence[int] | None = None,
    min_syllable_votes: int = 2,
    min_lex_votes: int = 2,
    default_font_pt: int = 0,
    font_pt_by_event: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Batch phrase events — one row per (event, surface_index)."""
    by_id = {str(e.get("event_id") or ""): e for e in entries}
    ids = list(event_ids) if event_ids else list(by_id.keys())
    font_map = font_pt_by_event or {}
    rows: list[dict[str, Any]] = []

    for eid in ids:
        entry = by_id.get(eid)
        if entry is None:
            continue
        for compose_entry, default_idx in phrase_event_probe_slices(entry):
            surfaces = phrase_event_surfaces(compose_entry)
            if not surfaces:
                continue
            if surface_indices and len(event_ids or []) == 1:
                indices = list(surface_indices)
            else:
                indices = [default_idx]
            for idx in indices:
                idx = max(0, min(idx, len(surfaces) - 1))
                phrase = surfaces[idx]
                fp = int(font_map.get(eid) or default_font_pt)
                row = read_phrase_on_store(
                    state,
                    event_entry=compose_entry,
                    phrase=phrase,
                    min_syllable_votes=min_syllable_votes,
                    min_lex_votes=min_lex_votes,
                    font_pt=fp,
                )
                row["event_id"] = eid
                row["surface_index"] = idx
                rows.append(row)
    return rows
