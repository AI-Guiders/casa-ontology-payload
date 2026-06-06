#!/usr/bin/env python3
"""Phrase gate on agent store — batch held-out events (ADR-0036 / teacher framework)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phrase_probe_runner import run_phrase_cases_on_store
from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = (
    _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"
)
_PROBE = "phrase-agent-store"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--event-id", action="append", default=[])
    p.add_argument("--min-syllable-votes", type=int, default=2)
    p.add_argument("--min-lex-votes", type=int, default=2)
    args = p.parse_args()

    setup_probe_imports()
    from teacher_pedagogy import PHRASE_AGENT_STORE_EVENTS, PHRASE_FONT_PT_BY_EVENT
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.phrase_compose import load_phrase_events

    entries = load_phrase_events(args.events)
    event_ids = tuple(args.event_id) if args.event_id else PHRASE_AGENT_STORE_EVENTS
    store = default_store(args.store)
    report_path = generated_report_path("teacher-phrase-agent-store.json")

    with store_session_lock(store, holder="probe:phrase-agent-store"):
        state = resolve_ingest_state(store, None)
        rows = run_phrase_cases_on_store(
            state,
            entries=entries,
            event_ids=event_ids,
            min_syllable_votes=args.min_syllable_votes,
            min_lex_votes=args.min_lex_votes,
            font_pt_by_event=PHRASE_FONT_PT_BY_EVENT,
        )

        phrase_know = sum(1 for r in rows if r.get("phrase_know"))
        know_words = sum(int(r.get("know_words") or 0) for r in rows)
        total_words = sum(int(r.get("total_words") or 0) for r in rows)

        out = {
            "store_id": args.store,
            "probe": _PROBE,
            "events_path": str(args.events),
            "event_ids": list(event_ids),
            "total_events": len(rows),
            "phrase_know_count": phrase_know,
            "phrase_know": phrase_know == len(rows) and bool(rows),
            "know_words": know_words,
            "total_words": total_words,
            "events": rows,
        }
        out = finalize_honest_probe_report(state, out, store=store, probe_id=_PROBE)

    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "phrase_know_count": phrase_know,
                "total_events": len(rows),
                "know_words": know_words,
                "total_words": total_words,
                "gate_kind": out.get("gate_kind"),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    if not out.get("probe_gate", {}).get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
