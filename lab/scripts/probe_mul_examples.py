#!/usr/bin/env python3
"""Probe user mul examples on math-l0-lab store (predict only, no oracle)."""

from __future__ import annotations

import json

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"

CUES = [
    "2+2+2=6",
    "2+2+2 = 2*3 = 6",
    "2+2=4",
    "2+2 = 2*2 = 4",
    "2*2=4",
    "2*3=6",
    "3*3=?",
    "3*3 = ?",
    "3*10=?",
    "3*10 = ?",
    "5*5=?",
    "5*5 = ?",
]

BRIDGE = [
    ("2+2=4", "4", "math.num.four", "mul_bridge: two twos add"),
    ("2*2=4", "4", "math.op.mul", "mul_bridge: two twos mul"),
    ("2+2+2=6", "6", "math.num.six", "mul_bridge: three twos add"),
    ("2*3=6", "6", "math.op.mul", "mul_bridge: three twos mul"),
    ("2+2+2 = 2*3 = 6", "6", "math.num.six", "mul_bridge: equiv"),
    ("2+2 = 2*2 = 4", "4", "math.num.four", "mul_bridge: equiv"),
]


def probe(label: str, state: dict, bundle: dict) -> list[dict]:
    print(f"\n=== {label} ===")
    rows: list[dict] = []
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    for cue in CUES:
        tick = predict_tick(state, cue, modality="schema", bundle=bundle)
        pred = tick.get("predict") or {}
        top = rank_cue_on_f0(dec, cue)[:4]
        row = {
            "cue": cue,
            "hypothesis": pred.get("hypothesis"),
            "verdict": tick.get("verdict"),
            "unbound": [u.get("op") for u in (pred.get("unbound_operators") or [])],
            "top4": top,
        }
        rows.append(row)
        print(
            f"{cue!r:28} → {row['hypothesis']!s:36} "
            f"({row['verdict']}) unbound={row['unbound']} top={top[:2]}"
        )
    return rows


def main() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    store = math_l0_lab_store(root=REPO_ROOT)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    before = probe("После curriculum (без mul_bridge)", state, bundle)

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
    rep = run_sleep(state, bundle)
    save_runtime_state(store, state)
    extract_kinds = [x.get("kind") for x in rep.get("items") or [] if x.get("extract")]
    print(f"\nsleep: merged={rep.get('merged')} extract_kinds={extract_kinds}")

    after = probe("После mul_bridge teach + sleep", state, bundle)

    out = {"before": before, "after": after, "sleep_merged": rep.get("merged")}
    report = REPO_ROOT / "lab/reports/mul-examples-probe.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nreport: {report}")


if __name__ == "__main__":
    main()
