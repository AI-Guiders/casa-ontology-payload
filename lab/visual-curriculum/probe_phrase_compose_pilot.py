#!/usr/bin/env python3
"""Refactored compose pilot — uses phrase_probe_runner + finalize_honest_probe_report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phrase_probe_runner import read_phrase_on_store
from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = (
    _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--event-id", default="")
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--surface-index", type=int, default=0)
    p.add_argument("--font-pt", type=int, default=0)
    p.add_argument("--min-syllable-votes", type=int, default=2)
    p.add_argument("--min-lex-votes", type=int, default=2)
    args = p.parse_args()

    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.phrase_compose import load_phrase_events
    from phrase_probe_runner import phrase_event_surfaces

    entries = load_phrase_events(args.events)
    if not entries:
        raise SystemExit(f"no entries in {args.events}")

    if args.event_id:
        entry = next((e for e in entries if e.get("event_id") == args.event_id), None)
        if entry is None:
            raise SystemExit(f"event not found: {args.event_id}")
    else:
        entry = entries[0]

    surfaces = phrase_event_surfaces(entry)
    if not surfaces:
        raise SystemExit("entry has no surfaces")
    idx = max(0, min(int(args.surface_index), len(surfaces) - 1))
    phrase = surfaces[idx]

    store = default_store(args.store)
    report_path = generated_report_path("teacher-phrase-compose-pilot.json")

    with store_session_lock(store, holder="probe:phrase-compose-pilot"):
        state = resolve_ingest_state(store, None)
        row = read_phrase_on_store(
            state,
            event_entry=entry,
            phrase=phrase,
            min_syllable_votes=args.min_syllable_votes,
            min_lex_votes=args.min_lex_votes,
            font_pt=args.font_pt,
        )
        out = {
            "store_id": args.store,
            "probe": "phrase-compose-pilot",
            "events_path": str(args.events),
            "event_id": entry.get("event_id"),
            "surface_index": idx,
            **row,
        }
        out = finalize_honest_probe_report(state, out, store=store, probe_id="phrase-compose-pilot")

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
                "gate_kind": out.get("gate_kind"),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
