#!/usr/bin/env python3
"""Autonomous T-loop on math-l0-lab store (no --fresh): predict → retain → sleep."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.prisms.memory.agent_autonomous_retain import maybe_autonomous_retain_tick
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, prism_hippo, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
DEFAULT_CUES = (
    "5, 10, 15, 20",
    "2, 4, 6, 8",
    "15",
    "||| - ||",
)


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def run_loop(*, rounds: int = 3, cues: tuple[str, ...] = DEFAULT_CUES) -> dict:
    store = math_l0_lab_store(root=REPO_ROOT)
    bundle = _bundle()
    state = ensure_prisms(load_field_state(field_state_path(store)))
    report: dict = {"store": str(store), "rounds": []}

    for r in range(rounds):
        round_rep: dict = {"round": r + 1, "ticks": [], "retained": [], "sleep": None}
        for cue in cues:
            tick = predict_tick(state, cue, modality="schema", bundle=bundle)
            round_rep["ticks"].append(
                {
                    "cue": cue,
                    "hypothesis": (tick.get("predict") or {}).get("hypothesis"),
                    "verdict": tick.get("verdict"),
                }
            )
            retained = maybe_autonomous_retain_tick(store, state, cue=cue, bundle=bundle, persist=False)
            if retained and not retained.get("skipped"):
                round_rep["retained"].append(retained)

        pending = len(prism_hippo(state).get("episodes") or [])
        if pending:
            sleep = run_sleep(state, bundle)
            save_runtime_state(store, state)
            round_rep["sleep"] = {"merged": sleep.get("merged"), "pending_before": pending}
        report["rounds"].append(round_rep)

    report["lattice_edges"] = len(memory_lattices(state).get("schema-math", {}).get("cells") or [])
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Autonomous math T-loop (existing store)")
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--cues", nargs="*", default=list(DEFAULT_CUES))
    args = p.parse_args()
    rep = run_loop(rounds=args.rounds, cues=tuple(args.cues))
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
