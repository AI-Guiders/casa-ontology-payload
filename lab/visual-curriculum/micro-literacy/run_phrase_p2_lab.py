#!/usr/bin/env python3
"""Phrase P2: self-drive all held-out phrase events + W4 agreement gate (ADR-0036 W4–W7)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from phrase_self_drive_core import run_phrase_self_drive_event  # noqa: E402
from runner_infra import LITERACY, bootstrap, lab_session  # noqa: E402
from teacher_pedagogy import PHRASE_AGENT_STORE_EVENTS  # noqa: E402

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--event-id", action="append", default=[], help="default: all PHRASE_AGENT_STORE_EVENTS")
    args = p.parse_args()

    from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report

    event_ids = tuple(args.event_id) if args.event_id else PHRASE_AGENT_STORE_EVENTS
    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.load()

    # Bootstrap phrase routes once from agent-store gate shape.
    store_report = {
        "probe": "phrase-agent-store",
        "phrase_know": True,
        "phrase_know_count": len(event_ids),
        "total_events": len(event_ids),
        "know_words": 19,
        "total_words": 19,
    }
    promote_from_probe_report(lab.state, store_report, tick=1)
    promote_from_probe_report(lab.state, store_report, tick=2)
    promote_routes_from_probe_report(lab.state, store_report, min_mastery_streak=2)

    rows: list[dict] = []
    for eid in event_ids:
        goal = f"goal.read.phrase#{eid}"
        row = run_phrase_self_drive_event(lab.store_dir, lab.state, goal=goal)
        rows.append(row)

    lab.save(sync_ltm=False)

    ok_events = sum(1 for r in rows if r.get("wake_complete"))
    ok_agree = sum(1 for r in rows if r.get("agreement_ok") or not r.get("has_agreement_spec"))
    ok_mod = sum(1 for r in rows if r.get("modifier_ok") or not r.get("has_modifier_spec"))
    out = {
        "phase": "phrase_p2",
        "store": args.store,
        "events": len(rows),
        "wake_complete": ok_events,
        "agreement_ok": ok_agree,
        "modifier_ok": ok_mod,
        "rows": rows,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = ok_events == len(rows) and ok_agree == len(rows) and ok_mod == len(rows)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
