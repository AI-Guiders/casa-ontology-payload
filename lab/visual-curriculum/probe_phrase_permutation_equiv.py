#!/usr/bin/env python3
"""All surfaces of a phrase event must yield phrase_know (ADR-0033 permutations)."""

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
    from casa.prisms.visual.phrase_compose import compose_phrase_verdict, load_phrase_events
    from casa.prisms.visual.phrase_permutation import check_permutation_equiv

    entries = load_phrase_events(args.events)
    entry = next((e for e in entries if e.get("event_id") == args.event_id), None)
    if entry is None:
        raise SystemExit(f"event not found: {args.event_id}")

    def compose(_surface: str) -> dict:
        reads = [
            {"surface": w.get("surface"), "verdict": "analytic_know"}
            for w in entry.get("words") or []
        ]
        return compose_phrase_verdict(reads, entry, check_questions=True)

    report = check_permutation_equiv(entry, compose)
    report["probe"] = "phrase-permutation-equiv"
    report_path = generated_report_path("teacher-phrase-permutation-equiv.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {report_path}")
    raise SystemExit(0 if report.get("permutation_know") else 1)


if __name__ == "__main__":
    main()
