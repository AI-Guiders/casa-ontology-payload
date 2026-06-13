#!/usr/bin/env python3
"""Replay impulse trace for von-neumann / Fable review (CASA-ADR-0080)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.nervous.impulse import read_impulse_trace
from casa.prisms.shared.store_layout import default_agent_store


def _print_row(doc: dict) -> None:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    winners = summary.get("winners") or doc.get("winners") or []
    print(
        f"tick={doc.get('tick_id')} channel={doc.get('channel')} "
        f"outcome={doc.get('outcome')} impulse_id={doc.get('impulse_id')}"
    )
    if winners:
        print(f"  winners: {', '.join(str(item) for item in winners)}")
    thresholds = summary.get("thresholds") or []
    if thresholds:
        print(f"  thresholds: {', '.join(str(item) for item in thresholds)}")
    events = doc.get("events") or []
    if events:
        print(f"  events: {len(events)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay CASA impulse trace jsonl")
    parser.add_argument("--store", type=Path, default=None, help="Agent store directory")
    parser.add_argument("--impulse-id", dest="impulse_id", default=None)
    parser.add_argument("--tick", type=int, default=None)
    parser.add_argument("--channel", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Print raw JSON lines")
    args = parser.parse_args()

    store = (args.store or default_agent_store()).resolve()
    rows = read_impulse_trace(
        store,
        impulse_id=args.impulse_id,
        tick_id=args.tick,
        channel=args.channel,
        limit=max(1, args.limit),
    )
    if not rows:
        print(f"No impulse trace rows in {store / 'nervous' / 'impulse_trace.jsonl'}", file=sys.stderr)
        return 1
    if args.json:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return 0
    for row in rows:
        _print_row(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
