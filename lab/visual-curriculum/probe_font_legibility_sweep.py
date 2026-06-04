#!/usr/bin/env python3
"""Sweep font pt: ephemeral 32x32 imprint + lex predict (trained bridges, no store write)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from font_legibility_lab import (
    DEFAULT_FONT_SIZES_PT,
    PILOT_SLUGS,
    WordSpec,
    estimate_threshold_pt,
    parse_font_sizes,
    predict_after_ephemeral_imprint,
    predict_stored_bridge,
    restore_visual_cells,
    snapshot_visual_cells,
    summarize_by_font,
    word_specs_from_manifest,
)
from probe_infra import default_store, generated_report_path, setup_probe_imports


def _run_sweep(
    *,
    words: list[WordSpec],
    font_sizes: tuple[int, ...],
    store_id: str,
    include_stored_baseline: bool,
    include_production_ephemeral: bool,
) -> dict:
    setup_probe_imports()
    from probe_lex_verdict import verdict_lex_probe

    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock

    store = default_store(store_id)
    items: list[dict] = []

    with store_session_lock(store, holder="probe:font-legibility-sweep"):
        state_word = resolve_ingest_state(store, None)
        for wi, word in enumerate(words, start=1):
            print(f"[sweep] word {wi}/{len(words)}: {word.surface} ({word.frame_id})", flush=True)
            vis_snap = snapshot_visual_cells(state_word)

            if include_stored_baseline:
                preds0 = predict_stored_bridge(state_word, word.frame_id)
                v0 = verdict_lex_probe(preds0, word.concept_id)
                items.append(
                    {
                        "mode": "stored",
                        "frame_id": word.frame_id,
                        "surface": word.surface,
                        "font_pt": word.production_font_pt,
                        "production_font_pt": word.production_font_pt,
                        "teacher_hint": word.concept_id,
                        "verdict": v0["verdict"],
                        "top_score": v0["top_score"],
                        "leaders": v0["leaders"],
                        "lex_top": [{"concept_id": c, "score": s} for c, s in preds0],
                    }
                )

            for font_pt in font_sizes:
                restore_visual_cells(state_word, vis_snap)
                preds, metrics = predict_after_ephemeral_imprint(
                    state_word,
                    frame_id=word.frame_id,
                    surface=word.surface,
                    font_pt=font_pt,
                )
                v = verdict_lex_probe(preds, word.concept_id)
                items.append(
                    {
                        "mode": "ephemeral",
                        "frame_id": word.frame_id,
                        "surface": word.surface,
                        "font_pt": font_pt,
                        "production_font_pt": word.production_font_pt,
                        "at_production_size": font_pt == word.production_font_pt,
                        "teacher_hint": word.concept_id,
                        "verdict": v["verdict"],
                        "top_score": v["top_score"],
                        "leaders": v["leaders"],
                        "lex_top": [{"concept_id": c, "score": s} for c, s in preds],
                        **metrics,
                    }
                )

            if include_production_ephemeral:
                pt = word.production_font_pt
                if pt not in font_sizes:
                    restore_visual_cells(state_word, vis_snap)
                    preds, metrics = predict_after_ephemeral_imprint(
                        state_word,
                        frame_id=word.frame_id,
                        surface=word.surface,
                        font_pt=pt,
                    )
                    v = verdict_lex_probe(preds, word.concept_id)
                    items.append(
                        {
                            "mode": "ephemeral_production",
                            "frame_id": word.frame_id,
                            "surface": word.surface,
                            "font_pt": pt,
                            "production_font_pt": pt,
                            "at_production_size": True,
                            "teacher_hint": word.concept_id,
                            "verdict": v["verdict"],
                            "top_score": v["top_score"],
                            "leaders": v["leaders"],
                            "lex_top": [{"concept_id": c, "score": s} for c, s in preds],
                            **metrics,
                        }
                    )

    by_font = summarize_by_font(items)
    threshold = estimate_threshold_pt(by_font)
    stored = [it for it in items if it.get("mode") == "stored"]
    return {
        "probe": "font-legibility-sweep",
        "store_id": store_id,
        "grid_note": "retinal_lrgb 32x32; ephemeral imprint per (word, font_pt); store not saved",
        "words": [{"frame_id": w.frame_id, "surface": w.surface, "production_font_pt": w.production_font_pt} for w in words],
        "font_sizes_pt": list(font_sizes),
        "by_font_pt": by_font,
        "threshold_heuristic": threshold,
        "stored_baseline": {
            "know": sum(1 for it in stored if it.get("verdict") == "know"),
            "total": len(stored),
        },
        "items": items,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann", dest="store_id")
    p.add_argument("--pilot", action="store_true", help="8 pilot words (lesson-03)")
    p.add_argument("--slugs", default="", help="comma slugs, e.g. mama,kot,девять")
    p.add_argument("--frame-ids", default="", help="explicit frame ids")
    p.add_argument(
        "--font-sizes",
        default=",".join(str(x) for x in DEFAULT_FONT_SIZES_PT),
        help="PIL pt sweep (comma-separated)",
    )
    p.add_argument("--no-stored-baseline", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()] or None
    frame_ids = [s.strip() for s in args.frame_ids.split(",") if s.strip()] or None
    if args.pilot:
        slugs = list(PILOT_SLUGS)
    if not slugs and not frame_ids:
        slugs = list(PILOT_SLUGS)

    words = word_specs_from_manifest(slugs=slugs, frame_ids=frame_ids)
    if not words:
        raise SystemExit("no words matched manifest (lang.word.*)")

    font_sizes = parse_font_sizes(args.font_sizes)
    report = _run_sweep(
        words=words,
        font_sizes=font_sizes,
        store_id=args.store_id,
        include_stored_baseline=not args.no_stored_baseline,
        include_production_ephemeral=False,
    )

    out_path = args.out or generated_report_path("teacher-font-legibility-sweep.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "path": str(out_path),
                "words": len(words),
                "font_steps": len(font_sizes),
                "stored_know": report["stored_baseline"],
                "threshold": report["threshold_heuristic"],
                "by_font_pt": report["by_font_pt"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
