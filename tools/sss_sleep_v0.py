#!/usr/bin/env python3
"""T_sleep: consolidate cyl_hippo → cyl_memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, hippo_episodes, run_sleep, save_state  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/sss-lattice-stack.v0.json"))
    p.add_argument("--strength", type=int, default=4)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    state = load_field_state(path)
    if not state:
        raise SystemExit("no field_state")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    before = len([e for e in hippo_episodes(state) if not e.get("consolidated")])
    state = ensure_cylinders(state)
    state["sn"] = {**(state.get("sn") or {}), "mode": "sleep"}
    report = run_sleep(state, bundle, stack_path=args.stack, strength=args.strength)
    save_state(path, state)
    print(
        json.dumps(
            {
                "mode": "sleep",
                "episodes_before": before,
                "report": report,
                "field_version": state.get("field_version"),
                "consolidation": state.get("consolidation"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
