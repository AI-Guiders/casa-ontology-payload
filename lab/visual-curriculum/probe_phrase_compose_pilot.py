#!/usr/bin/env python3
"""P1 phrase compose: per-word analytic R1 on phrase crop + slots + agreement (ADR-0033)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from font_legibility_lab import production_font_pt, restore_visual_cells, snapshot_visual_cells
from probe_infra import default_store, generated_report_path, setup_probe_imports
from phrase_crop import crop_word_rgb, phrase_word_boxes, render_phrase_rgb

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = (
    _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--surface-index", type=int, default=0, help="index into entry.surfaces[]")
    p.add_argument("--font-pt", type=int, default=0)
    p.add_argument("--min-syllable-votes", type=int, default=2)
    p.add_argument("--min-lex-votes", type=int, default=2)
    args = p.parse_args()

    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.analytic_read import compose_analytic_read
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue
    from casa.prisms.visual.phrase_compose import (
        analytic_entry_from_word,
        compose_phrase_verdict,
        load_phrase_events,
        phrase_probe_frame_id,
    )
    from casa.prisms.visual.imprint import imprint_visual_frame
    from font_legibility_lab import lum_imprint_metrics

    entries = load_phrase_events(args.events)
    if not entries:
        raise SystemExit(f"no entries in {args.events}")

    entry = entries[0]
    surfaces = list(entry.get("surfaces") or [])
    if not surfaces:
        raise SystemExit("entry has no surfaces")
    idx = max(0, min(int(args.surface_index), len(surfaces) - 1))
    phrase = str(surfaces[idx]).strip()

    store = default_store(args.store)
    report_path = generated_report_path("teacher-phrase-compose-pilot.json")

    with store_session_lock(store, holder="probe:phrase-compose-pilot"):
        state = resolve_ingest_state(store, None)
        vis_snap = snapshot_visual_cells(state)

        font_pt = int(args.font_pt) if int(args.font_pt) > 0 else int(production_font_pt(phrase))
        phrase_rgb = render_phrase_rgb(phrase, font_pt)
        boxes = phrase_word_boxes(phrase, font_pt)
        box_by_word = {_normalize_word(b["word"]): b for b in boxes}

        word_reads: list[dict[str, Any]] = []
        for spec in entry.get("words") or []:
            surface = str(spec.get("surface") or "")
            key = _normalize_word(surface)
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

            entry = analytic_entry_from_word(spec)
            if entry is None:
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
                entry,
                novel_preds=novel_preds,
                novel_metrics=metrics,
                min_syllable_votes=args.min_syllable_votes,
                min_lex_votes=args.min_lex_votes,
                predict=predict_lex_for_vis_cue,
            )
            row["phrase_frame_id"] = fid
            row["bbox"] = box["bbox"]
            word_reads.append(row)
            restore_visual_cells(state, vis_snap)

        composed = compose_phrase_verdict(word_reads, entry)

    out = {
        "store_id": args.store,
        "probe": "phrase-compose-pilot",
        "events_path": str(args.events),
        "event_id": entry.get("event_id"),
        "phrase": phrase,
        "surface_index": idx,
        "font_pt": font_pt,
        "verdict": composed["verdict"],
        "phrase_know": composed["phrase_know"],
        "slots": composed["slots"],
        "agreement": composed["agreement"],
        "word_reads": word_reads,
        "total_words": len(word_reads),
        "know_words": sum(1 for r in word_reads if r.get("verdict") == "analytic_know"),
    }
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from casa.domain.emergent_promote import record_probe_gate
    from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

    gate = record_probe_gate(state, out, tick=int(state.get("field_version") or 0), store_dir=store)
    out["probe_gate"] = {"gate": gate.gate, "passed": gate.passed}
    if gate.skipped:
        out["probe_gate"]["skipped"] = gate.skipped
    if gate.passed:
        mark_runtime_dirty(state)
        save_runtime_state(store, state, force=True, sync_ltm_on_save=False)
        report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "probe": out["probe"],
                "phrase": phrase,
                "verdict": out["verdict"],
                "phrase_know": out["phrase_know"],
                "know_words": out["know_words"],
                "total_words": out["total_words"],
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )


def _normalize_word(word: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", word.strip()).lower()


if __name__ == "__main__":
    main()
