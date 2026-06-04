#!/usr/bin/env python3
"""Три смысла «знания слова»: мост / только след / неученое слово (без семантики)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from font_legibility_lab import (
    WordSpec,
    novel_probe_frame_id,
    parse_font_sizes,
    predict_after_ephemeral_imprint_variant,
    predict_lex_variant,
    production_font_pt,
    restore_visual_cells,
    snapshot_visual_cells,
    top_grapheme_syllable,
    word_specs_from_manifest,
)
from probe_infra import default_store, generated_report_path, setup_probe_imports

# Режимы (см. design/CASA-literacy-font-legibility-experiment-v1.md § «Три смысла»)
MODES: dict[str, dict[str, Any]] = {
    "L1_trained_bridge": {
        "label": "Учили целое слово: мост vis↔lang.word (отличить от других)",
        "frame": "trained",
        "bridges": "full",
        "what_it_tests": "discrimination + память урока, не семантика",
    },
    "L2_imprint_cells": {
        "label": "Тот же смысл, novel frame_id, только lum E:-токены (без рёбер lexicon)",
        "frame": "novel",
        "bridges": "cells_only",
        "what_it_tests": "32×32 след + слабая активация без учебного frame_id",
    },
    "L3_never_ingested": {
        "label": "Слово из корпуса, но novel frame (урока на этот id не было)",
        "frame": "novel",
        "bridges": "full",
        "what_it_tests": "нет целого моста; возможны grapheme/syllable, не lang.word",
    },
}


def _run(
    *,
    words: list[WordSpec],
    font_sizes: tuple[int, ...],
    store_id: str,
    modes: tuple[str, ...],
) -> dict[str, Any]:
    setup_probe_imports()
    from probe_lex_verdict import verdict_lex_probe

    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock

    store = default_store(store_id)
    items: list[dict[str, Any]] = []

    with store_session_lock(store, holder="probe:word-recognition-modes"):
        state = resolve_ingest_state(store, None)
        vis_snap = snapshot_visual_cells(state)

        for word in words:
            trained_fid = word.frame_id
            novel_fid = novel_probe_frame_id(word)
            for font_pt in font_sizes:
                for mode_key in modes:
                    spec = MODES[mode_key]
                    fid = trained_fid if spec["frame"] == "trained" else novel_fid
                    bridges = str(spec["bridges"])
                    restore_visual_cells(state, vis_snap)
                    preds, metrics = predict_after_ephemeral_imprint_variant(
                        state,
                        frame_id=fid,
                        surface=word.surface,
                        font_pt=font_pt,
                        bridges=bridges,
                    )
                    v = verdict_lex_probe(preds, word.concept_id)
                    items.append(
                        {
                            "mode": mode_key,
                            "mode_label": spec["label"],
                            "frame_id": fid,
                            "trained_frame_id": trained_fid,
                            "surface": word.surface,
                            "font_pt": font_pt,
                            "production_font_pt": word.production_font_pt,
                            "teacher_hint": word.concept_id,
                            "verdict": v["verdict"],
                            "top_score": v["top_score"],
                            "leaders": v["leaders"],
                            "lex_top": [{"concept_id": c, "score": s} for c, s in preds],
                            "grapheme_syllable_top": top_grapheme_syllable(preds),
                            **metrics,
                        }
                    )

            # stored L1 без переimprint
            restore_visual_cells(state, vis_snap)
            preds_st = predict_lex_variant(state, trained_fid, bridges="full")
            v_st = verdict_lex_probe(preds_st, word.concept_id)
            items.append(
                {
                    "mode": "L1_stored_jpeg",
                    "mode_label": "Учебный JPEG в памяти (без перерисовки)",
                    "frame_id": trained_fid,
                    "trained_frame_id": trained_fid,
                    "surface": word.surface,
                    "font_pt": word.production_font_pt,
                    "production_font_pt": word.production_font_pt,
                    "teacher_hint": word.concept_id,
                    "verdict": v_st["verdict"],
                    "top_score": v_st["top_score"],
                    "leaders": v_st["leaders"],
                    "lex_top": [{"concept_id": c, "score": s} for c, s in preds_st],
                    "grapheme_syllable_top": top_grapheme_syllable(preds_st),
                }
            )

    return {
        "probe": "word-recognition-modes",
        "store_id": store_id,
        "modes_explained": MODES,
        "words": [
            {
                "surface": w.surface,
                "trained_frame_id": w.frame_id,
                "novel_frame_id": novel_probe_frame_id(w),
                "concept_id": w.concept_id,
                "production_font_pt": w.production_font_pt,
            }
            for w in words
        ],
        "font_sizes_pt": list(font_sizes),
        "items": items,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann", dest="store_id")
    p.add_argument("--frame-ids", required=True, help="trained frame, comma-separated")
    p.add_argument(
        "--font-sizes",
        default="8,24,48,96,120,160,200",
        help="ключевые pt для сравнения",
    )
    p.add_argument(
        "--modes",
        default="L1_trained_bridge,L2_imprint_cells,L3_never_ingested",
        help="comma keys from MODES",
    )
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    frame_ids = [s.strip() for s in args.frame_ids.split(",") if s.strip()]
    words = word_specs_from_manifest(frame_ids=frame_ids)
    if not words:
        raise SystemExit("no frames")

    modes = tuple(s.strip() for s in args.modes.split(",") if s.strip())
    for m in modes:
        if m not in MODES and m != "L1_stored_jpeg":
            raise SystemExit(f"unknown mode {m!r}")

    font_sizes = parse_font_sizes(args.font_sizes)
    report = _run(words=words, font_sizes=font_sizes, store_id=args.store_id, modes=modes)

    out = args.out or generated_report_path("teacher-word-recognition-modes.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(out), "words": len(words), "items": len(report["items"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
