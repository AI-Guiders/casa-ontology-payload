#!/usr/bin/env python3
"""Question-frame gate on phrase event slots (ADR-0033 §6)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import run_spec_regression, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--event-id", default="lang.event.transitive.wash.v0")
    args = p.parse_args()

    setup_probe_imports()
    from casa.prisms.visual.phrase_compose import bind_slots, load_phrase_events
    from casa.prisms.visual.phrase_question import compose_question_verdict

    entry = next(
        (e for e in load_phrase_events(args.events) if e.get("event_id") == args.event_id),
        None,
    )
    if entry is None:
        raise SystemExit(f"event not found: {args.event_id}")

    reads = [{"surface": w.get("surface"), "verdict": "analytic_know"} for w in entry.get("words") or []]
    slots = bind_slots(reads, list(entry.get("words") or []))["slots"]
    raw = compose_question_verdict(slots, entry)
    raw["probe"] = "question-frame-pilot"
    report = run_spec_regression(raw, report_filename="teacher-question-frame-pilot.json")
    raise SystemExit(0 if report.get("verdict_pass") else 1)


if __name__ == "__main__":
    main()
