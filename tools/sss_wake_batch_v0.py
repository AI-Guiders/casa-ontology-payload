#!/usr/bin/env python3
"""Batch T_wake with auto-episode when babble ≠ target."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, save_state  # type: ignore
from sss_wake_v0 import wake_turn  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--episodes", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--auto", action=argparse.BooleanOptionalAction, default=True)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    items = json.loads(args.episodes.read_text(encoding="utf-8"))

    state = ensure_cylinders(load_field_state(path))
    report: list[dict] = []
    recorded = 0
    skipped = 0

    for item in items:
        lattice = str(item.get("lattice") or "L1_syllable")
        cue = str(item.get("cue") or "")
        target = str(item.get("target") or item.get("teacher") or "")
        auto = item.get("auto", args.auto)
        force = bool(item.get("force_episode"))
        turn = wake_turn(
            state,
            cue=cue,
            lattice_id=lattice,
            target=target or None,
            bundle=bundle,
            auto=bool(auto),
            force_episode=force,
        )
        if turn.get("episode"):
            recorded += 1
        elif target:
            skipped += 1
        report.append(turn)

    save_state(path, state)
    print(
        json.dumps(
            {
                "turns": len(report),
                "episodes_recorded": recorded,
                "skipped_correct": skipped,
                "hippo_pending": len(state["cylinders"]["cyl_hippo"]["episodes"]),
                "items": report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
