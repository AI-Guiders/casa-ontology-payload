#!/usr/bin/env python3
"""Generic block gate — frame held-out or phrase-agent-store (block spec JSON)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import manifest_hints, run_frame_probe, setup_probe_imports

setup_probe_imports()

from block_pedagogy import (  # noqa: E402
    block_kind,
    gate_pass,
    held_out_frame_ids,
    held_out_phrase_event_ids,
    load_block_spec,
    register_bind_report,
    morph_segment_bind_report,
    register_meta_bind_report,
)


def _run_phrase_gate(spec: dict[str, Any], *, block_id: str, store_id: str) -> dict:
    from teacher_pedagogy import PHRASE_AGENT_STORE_EVENTS

    from probe_infra import setup_probe_imports

    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.phrase_compose import load_phrase_events
    from phrase_probe_runner import run_phrase_cases_on_store
    from probe_infra import default_store, finalize_honest_probe_report, generated_report_path

    event_ids = held_out_phrase_event_ids(spec) or list(PHRASE_AGENT_STORE_EVENTS)
    probe_id = str((spec.get("gate") or {}).get("probe_id") or "phrase-agent-store")
    events_path = spec.get("events_path")
    path = (
        Path(__file__).resolve().parents[2] / str(events_path)
        if events_path
        else Path(__file__).resolve().parents[2]
        / "lessons/literacy-cards/data/literacy/phrase-events-ru-pilot-v1.json"
    )
    entries = load_phrase_events(path)
    store = default_store(store_id)
    report_name = f"teacher-probe-{block_id}-phrase-gate.json"

    with store_session_lock(store, holder=f"probe:{probe_id}"):
        state = resolve_ingest_state(store, None)
        rows = run_phrase_cases_on_store(state, entries=entries, event_ids=tuple(event_ids))
        phrase_know = sum(1 for r in rows if r.get("phrase_know"))
        report = {
            "store_id": store_id,
            "probe": probe_id,
            "block_id": spec.get("block_id"),
            "events_path": str(path),
            "event_ids": event_ids,
            "total_events": len(rows),
            "phrase_know_count": phrase_know,
            "phrase_know": phrase_know == len(rows) and bool(rows),
            "events": rows,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=probe_id)

    report["gate_pass"] = gate_pass(spec, report)
    out_path = generated_report_path(report_name)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _run_frame_gate(spec: dict[str, Any], *, block_id: str, store_id: str) -> dict:
    frame_ids = held_out_frame_ids(spec)
    if not frame_ids:
        raise SystemExit(f"no held-out frames for block {block_id!r}")

    class_rel = str(spec.get("class_rel") or "lessons/literacy-cards")
    hints = manifest_hints(class_rel)
    probe_id = str((spec.get("gate") or {}).get("probe_id") or f"probe_{block_id.replace('-', '_')}_held_out")
    report_name = f"teacher-probe-{block_id}-held-out.json"

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    report = run_frame_probe(
        probe=probe_id,
        frames=frame_ids,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename=report_name,
        lock_holder=f"probe:{probe_id}",
        preds_field="lex_top",
        store_id=store_id,
        extra_out={
            "block_id": spec.get("block_id"),
            "held_out": True,
            "held_out_count": len(frame_ids),
        },
        print_lines=False,
    )
    from probe_infra import default_store, setup_probe_imports

    meta_rules = spec.get("register_meta_rules") or []
    morph_rules = spec.get("morph_meta_rules") or []
    pairs = spec.get("register_bind_pairs") or []
    if meta_rules or morph_rules or pairs:
        setup_probe_imports()
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(default_store(store_id), None)
        if meta_rules:
            report["register_meta_bind"] = register_meta_bind_report(state, meta_rules)
        if morph_rules:
            report["morph_segment_bind"] = morph_segment_bind_report(state, morph_rules)
        if pairs:
            report["register_bind"] = register_bind_report(state, pairs)
    report["gate_pass"] = gate_pass(spec, report)
    out_path = Path(__file__).resolve().parent / "generated" / report_name
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--block", default="block-01-grapheme-cyrl")
    p.add_argument("--spec", type=Path, default=None)
    p.add_argument("--store", default="von-neumann")
    args = p.parse_args()

    block_id = args.block
    spec = load_block_spec(args.spec, block_id=block_id)
    if block_kind(spec) == "phrase":
        report = _run_phrase_gate(spec, block_id=block_id, store_id=args.store)
        summary = {
            "probe": report.get("probe"),
            "block": spec.get("block_id"),
            "phrase_know_count": report.get("phrase_know_count"),
            "total_events": report.get("total_events"),
            "gate_pass": report.get("gate_pass"),
        }
    else:
        report = _run_frame_gate(spec, block_id=block_id, store_id=args.store)
        summary = {
            "probe": report.get("probe"),
            "block": spec.get("block_id"),
            "know": report.get("know"),
            "total": report.get("total"),
            "gate_pass": report.get("gate_pass"),
        }
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
