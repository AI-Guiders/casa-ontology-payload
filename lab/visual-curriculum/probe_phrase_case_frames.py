#!/usr/bin/env python3
"""Case gate via question-frames + role slots (ADR-0033; not isolated table quiz)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--event-id", default="lang.event.transitive.wash.v0")
    args = p.parse_args()

    setup_probe_imports()
    from casa.prisms.visual.phrase_case import compose_case_verdict
    from casa.prisms.visual.phrase_compose import bind_slots, load_phrase_events

    entry = next(
        (e for e in load_phrase_events(args.events) if e.get("event_id") == args.event_id),
        None,
    )
    if entry is None:
        raise SystemExit(f"event not found: {args.event_id}")

    reads = [{"surface": w.get("surface"), "verdict": "analytic_know"} for w in entry.get("words") or []]
    slots = bind_slots(reads, list(entry.get("words") or []))["slots"]
    report = compose_case_verdict(slots, entry)
    report["probe"] = "phrase-case-frames"
    report_path = generated_report_path("teacher-phrase-case-frames.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {report_path}")
    raise SystemExit(0 if report.get("case_know") else 1)


if __name__ == "__main__":
    main()
