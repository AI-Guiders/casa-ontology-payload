#!/usr/bin/env python3
"""Numeral phrase events — examples + rule gate (ADR-0033)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_EVENTS = _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"
_NUMERAL_PREFIX = "lang.event.numeral."


def _iter_examples(entry: dict) -> list[tuple[dict, dict]]:
    examples = entry.get("examples")
    if isinstance(examples, list) and examples:
        return [(entry, ex) for ex in examples if isinstance(ex, dict)]
    return [(entry, entry)]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, default=_DEFAULT_EVENTS)
    p.add_argument("--event-id", default="")
    args = p.parse_args()

    setup_probe_imports()
    from casa.prisms.visual.phrase_compose import compose_phrase_verdict, load_phrase_events
    from casa.prisms.visual.phrase_numeral import resolve_numeral_entry

    entries = load_phrase_events(args.events)
    if args.event_id:
        entries = [e for e in entries if e.get("event_id") == args.event_id]
    else:
        entries = [e for e in entries if str(e.get("event_id") or "").startswith(_NUMERAL_PREFIX)]

    if not entries:
        raise SystemExit("no numeral events found")

    rows: list[dict] = []
    ok = True
    for entry in entries:
        eid = str(entry.get("event_id") or "")
        for _parent, example in _iter_examples(entry):
            reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in example.get("words") or []]
            merged = resolve_numeral_entry(entry, reads)
            out = compose_phrase_verdict(reads, entry)
            row_ok = bool(out.get("phrase_know"))
            if not row_ok:
                ok = False
            label = example.get("lemma") or example.get("surfaces", [""])[0]
            rows.append(
                {
                    "event_id": eid,
                    "example": label,
                    "surfaces": merged.get("surfaces"),
                    "phrase_know": row_ok,
                    "verdict": out.get("verdict"),
                }
            )

    report = {
        "probe": "numeral-pilot",
        "total": len(rows),
        "know": sum(1 for r in rows if r.get("phrase_know")),
        "pass": ok,
        "rows": rows,
    }
    path = generated_report_path("teacher-numeral-pilot.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {path}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
