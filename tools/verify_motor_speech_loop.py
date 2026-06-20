#!/usr/bin/env python3
"""Verify motor speech stub loop: plan → self-listen → field bridge (ADR-0082)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.prisms.auditory.bridge_motor import bind_motor_heard_on_tick
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.motor.speech_tick import maybe_motor_speech_on_tick


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify motor speech self-listen loop (no TTS).")
    parser.add_argument("--store", type=Path, default=None, help="Agent store dir (temp if omitted)")
    parser.add_argument("--ticks", type=int, default=1, help="Babble ticks to run")
    args = parser.parse_args()

    cleanup = False
    if args.store is None:
        tmp = tempfile.mkdtemp(prefix="casa-motor-verify-")
        store = Path(tmp)
        cleanup = True
    else:
        store = args.store.resolve()
        store.mkdir(parents=True, exist_ok=True)

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state["motor_speech"] = {"enabled": True, "babble": True, "babble_only": True}

    reports: list[dict] = []
    for tick in range(1, max(1, args.ticks) + 1):
        rep = maybe_motor_speech_on_tick(store, state, tick=tick, force=True)
        bind = bind_motor_heard_on_tick(state)
        reports.append({"tick": tick, "motor": rep, "bind": bind})

    ok = all(r["motor"].get("spoken") for r in reports)
    summary = {
        "ok": ok,
        "store": str(store),
        "ticks": len(reports),
        "field_version": state.get("field_version"),
        "last_plan": (reports[-1]["motor"].get("plan") if reports else None),
        "reports": reports,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if cleanup:
        print(f"(temp store: {store})", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
