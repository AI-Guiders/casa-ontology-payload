#!/usr/bin/env python3
"""Self-correct session: babble → internal mismatch → hippo → optional sleep → retry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_babble_v0 import babble_from_sss  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, run_sleep, save_state  # type: ignore
from sss_wake_util import babble_matches_target, internal_target_from_cue  # type: ignore
from sss_wake_v0 import wake_turn  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True, help="JSON array: {cue, lattice}")
    p.add_argument("--sleep-after", action="store_true")
    p.add_argument("--retry", action="store_true", help="babble again after sleep")
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    items = json.loads(args.cues.read_text(encoding="utf-8"))

    state = ensure_cylinders(load_field_state(path))
    turns: list[dict] = []
    self_eps = 0

    for item in items:
        lattice = str(item.get("lattice") or "L1_syllable")
        cue = str(item.get("cue") or "")
        turn = wake_turn(state, cue=cue, lattice_id=lattice, bundle=bundle, auto=True, self_correct=True)
        if turn.get("self_episode"):
            self_eps += 1
        turns.append(turn)

    sleep_report = None
    if args.sleep_after and self_eps:
        sleep_report = run_sleep(state, bundle)

    retries: list[dict] = []
    if args.retry:
        for item in items:
            lattice = str(item.get("lattice") or "L1_syllable")
            cue = str(item.get("cue") or "")
            wake = babble_from_sss(state, lattice_id=lattice, prompt=cue)
            internal = internal_target_from_cue(cue, lattice_id=lattice)
            retries.append(
                {
                    "cue": cue,
                    "internal_target": internal,
                    "matched": babble_matches_target(wake, internal, lattice_id=lattice),
                    "babble_surface": wake.get("active", [{}])[0] if wake.get("active") else None,
                }
            )

    save_state(path, state)
    print(
        json.dumps(
            {
                "turns": len(turns),
                "self_episodes": self_eps,
                "sleep": sleep_report,
                "retries": retries,
                "items": turns,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
