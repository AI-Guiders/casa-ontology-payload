#!/usr/bin/env python3
"""Твои примеры mul: teach bridge → predict (абстракция count×step)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_cardinal_abstract import abstract_cardinal_magnitude, parse_mul_cue
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"

EXAMPLES = [
    "2+2+2=6",
    "2+2+2 = 2*3 = 6",
    "2+2=4",
    "2+2 = 2*2 = 4",
    "2*2=4",
    "2*3=6",
    "3*3=?",
    "3*10=?",
    "5*5=?",
]

BRIDGE = [
    ("2+2=4", "4", "math.num.four", "mul: дважды по два"),
    ("2*2=4", "4", "math.op.mul", "mul: дважды по два"),
    ("2+2+2=6", "6", "math.num.six", "mul: трижды по два"),
    ("2*3=6", "6", "math.op.mul", "mul: трижды по два"),
    ("2+2+2 = 2*3 = 6", "6", "math.num.six", "mul: add=mul same scene"),
    ("2+2 = 2*2 = 4", "4", "math.num.four", "mul: add=mul same scene"),
]


def main() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    store = math_l0_lab_store(root=REPO_ROOT)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    print("=== ДО bridge (только curriculum) ===\n")
    for cue in EXAMPLES:
        t = predict_tick(state, cue, modality="schema")
        h = (t.get("predict") or {}).get("hypothesis")
        u = [x.get("op") for x in (t.get("predict") or {}).get("unbound_operators") or []]
        print(f"  {cue:26} → {h!s:32}  unbound={u}")

    for cue, correct, cid, scene in BRIDGE:
        append_episode(
            state,
            cue=cue,
            surface_attempt="?",
            correct=correct,
            lattice_id="schema-math",
            concept_id=cid,
            correction_kind="mul_bridge",
            scene=scene,
        )
    run_sleep(state, bundle)
    save_runtime_state(store, state)

    print("\n=== ПОСЛЕ bridge + sleep ===\n")
    for cue in EXAMPLES:
        t = predict_tick(state, cue, modality="schema")
        h = (t.get("predict") or {}).get("hypothesis")
        u = [x.get("op") for x in (t.get("predict") or {}).get("unbound_operators") or []]
        extra = ""
        p = parse_mul_cue(cue)
        if p:
            s, c = p
            mag = abstract_cardinal_magnitude(step=s, count=c)
            extra = f"  [абстракция: {c}× по {s} → мощность {mag}]"
        print(f"  {cue:26} → {h!s:32}  unbound={u}{extra}")


if __name__ == "__main__":
    main()
