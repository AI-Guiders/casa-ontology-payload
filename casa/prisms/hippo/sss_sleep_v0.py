#!/usr/bin/env python3
"""T_sleep: consolidate prism_hippo → prism_memory."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.field_bus import ConsolidatePhaseEvent, publish
from casa.prisms.hippo.sleep_replay_v0 import PRODUCTION_SLEEP_REPLAY, SleepReplayConfig
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, hippo_episodes, run_sleep, save_state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/sss-lattice-stack.v0.json"))
    p.add_argument("--strength", type=int, default=4)
    p.add_argument(
        "--replay-k",
        type=int,
        default=PRODUCTION_SLEEP_REPLAY.replay_k,
        help="spaced rehearsal batch size before merge (0 = archive only)",
    )
    p.add_argument(
        "--replay-value-weight",
        type=float,
        default=PRODUCTION_SLEEP_REPLAY.value_weight,
        help="value tag weight in replay priority (ADR-0010)",
    )
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    state = load_field_state(path)
    if not state:
        raise SystemExit("no field_state")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    before = len([e for e in hippo_episodes(state) if not e.get("consolidated")])
    state = ensure_prisms(state)
    state["sn"] = {**(state.get("sn") or {}), "mode": "sleep"}
    report = run_sleep(
        state,
        bundle,
        stack_path=args.stack,
        strength=args.strength,
        replay_k=args.replay_k,
        replay_value_weight=args.replay_value_weight,
    )
    save_state(path, state)
    shards = int((report or {}).get("merged_episodes") or (report or {}).get("episodes_merged") or 0)
    publish(
        ConsolidatePhaseEvent(
            store_id=store.name,
            phase="sleep",
            field_version=int(state.get("field_version") or 0),
            shards_trained=shards,
            detail={"episodes_before": before, "report_keys": sorted((report or {}).keys())},
        )
    )
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
