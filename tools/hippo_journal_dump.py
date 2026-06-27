#!/usr/bin/env python3
"""Dump ADR-0088 hippo_index journal and moment buffer from agent store."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.prisms.hippo.mode import get_hippo_mode
from casa.prisms.hippo.wake_index import ensure_hippo_index
from casa.prisms.memory.agent_life import load_unified_agent_runtime
from casa.prisms.shared.store_layout import default_agent_store


def summarize_hippo_index(state: dict[str, Any], *, tail: int = 40) -> dict[str, Any]:
    idx = ensure_hippo_index(state)
    journal = [row for row in (idx.get("journal") or []) if isinstance(row, dict)]
    events: dict[str, int] = {}
    for row in journal:
        ev = str(row.get("event") or "")
        events[ev] = events.get(ev, 0) + 1
    buffer = idx.get("moment_buffer") or {}
    buffer_summary: dict[str, Any] = {}
    if isinstance(buffer, dict):
        for mid, row in buffer.items():
            if not isinstance(row, dict):
                continue
            ticks = row.get("ticks") or []
            buffer_summary[str(mid)] = {
                "scene_id": row.get("scene_id"),
                "beat_id": row.get("beat_id"),
                "modalities": row.get("modalities") or [],
                "tick_count": len(ticks) if isinstance(ticks, list) else 0,
            }
    return {
        "hippo_mode": get_hippo_mode(state),
        "active_episode_id": idx.get("active_episode_id"),
        "active_moment_id": idx.get("active_moment_id"),
        "active_scene_id": idx.get("active_scene_id"),
        "active_beat_id": idx.get("active_beat_id"),
        "moment_buffer": buffer_summary,
        "journal_len": len(journal),
        "journal_events": events,
        "journal_tail": journal[-max(0, int(tail)) :],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump hippo_index episodic wake journal from store")
    parser.add_argument("--store-dir", type=Path, default=None)
    parser.add_argument("--tail", type=int, default=40, help="journal rows from end")
    parser.add_argument("--out", type=Path, default=None, help="write JSON to file instead of stdout")
    args = parser.parse_args()

    store_dir = (args.store_dir or default_agent_store()).resolve()
    runtime = load_unified_agent_runtime(store_dir)
    out = summarize_hippo_index(runtime.state, tail=args.tail)
    out["store_dir"] = str(store_dir)

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
