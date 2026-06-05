#!/usr/bin/env python3
"""R1 analytic read: syllable chain know + lang.word in LTM; novel probe frame (ADR-0032)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from font_legibility_lab import (
    predict_after_ephemeral_imprint_variant,
    production_font_pt,
    restore_visual_cells,
    snapshot_visual_cells,
)
from literacy_lab_io import analytic_entries_for_slugs, slugs_from_phrase_events
from probe_infra import default_store, generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--font-pt", type=int, default=0, help="0 = production size per word")
    p.add_argument("--min-syllable-votes", type=int, default=2)
    p.add_argument("--min-lex-votes", type=int, default=2)
    p.add_argument("--slug", action="append", default=[], help="Corpus slug(s); default = phrase P1")
    args = p.parse_args()

    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.analytic_read import compose_analytic_read
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

    slugs = [str(s).strip() for s in args.slug] if args.slug else slugs_from_phrase_events()
    entries = analytic_entries_for_slugs(slugs)
    store = default_store(args.store)
    report_path = generated_report_path("teacher-analytic-read.json")
    counts: dict[str, int] = {}
    novel_counts: dict[str, int] = {}

    with store_session_lock(store, holder="probe:analytic-read-corpus"):
        state = resolve_ingest_state(store, None)
        vis_snap = snapshot_visual_cells(state)
        items: list[dict[str, Any]] = []

        for entry in entries:
            slug = str(entry.get("slug") or "")
            surface = str(entry.get("surface") or "")
            font_pt = args.font_pt or production_font_pt(surface)
            restore_visual_cells(state, vis_snap)
            novel_preds, metrics = predict_after_ephemeral_imprint_variant(
                state,
                frame_id=f"analytic-probe-{slug}-sans",
                surface=surface,
                font_pt=font_pt,
                top_k=8,
                bridges="full",
            )
            row = compose_analytic_read(
                state,
                entry,
                novel_preds=novel_preds,
                novel_metrics=metrics,
                min_syllable_votes=args.min_syllable_votes,
                min_lex_votes=args.min_lex_votes,
                predict=predict_lex_for_vis_cue,
            )
            row["font_pt"] = font_pt
            v = str(row.get("verdict") or "empty")
            counts[v] = counts.get(v, 0) + 1
            nv = str(row.get("r1_novel_via") or "none")
            if row.get("r1_novel_bind"):
                novel_counts[nv] = novel_counts.get(nv, 0) + 1
            items.append(row)
            print(
                f"{surface}: chain={row['chain']['chain_know']} "
                f"ltm={row['lex_in_ltm']} novel={row.get('r1_novel_bind')} "
                f"via={row.get('via')} r1={nv}"
            )

    out = {
        "store_id": args.store,
        "probe": "analytic-read-corpus-r1",
        "segments_path": "corpus:phrase-p1",
        "counts": counts,
        "r1_novel_bind": novel_counts,
        "total": len(items),
        "items": items,
    }
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    from casa.domain.emergent_promote import record_probe_gate
    from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

    gate = record_probe_gate(state, out, store_dir=store)
    out["probe_gate"] = {"gate": gate.gate, "passed": gate.passed}
    if gate.passed:
        mark_runtime_dirty(state)
        save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {"counts": counts, "r1_novel_bind": novel_counts, "total": len(items), "path": str(report_path)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
