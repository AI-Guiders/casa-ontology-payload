#!/usr/bin/env python3
"""Teacher episodes: sticks + numeric + roman lesson series on math-l0-lab."""

from __future__ import annotations

import json
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, math_l0_lab_store
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def main() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    store = math_l0_lab_store(root=REPO_ROOT)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    lessons = [
        {"cue": "|| + || = ||||", "correct": "||||", "concept_id": "math.op.add", "scene": "sticks_add"},
        {"cue": "| + | = ||", "correct": "||", "concept_id": "math.op.add", "scene": "sticks_add"},
        {"cue": "2 + 2 = 4", "correct": "4", "concept_id": "math.op.add", "scene": "numeric_add"},
        {"cue": "1 + 1 = 2", "correct": "2", "concept_id": "math.op.add", "scene": "numeric_add"},
        {"cue": "I + III = IV", "correct": "IV", "concept_id": "math.op.add", "scene": "roman_add"},
        {"cue": "II + II = IV", "correct": "IV", "concept_id": "math.op.add", "scene": "roman_add"},
        {"cue": "I + III = ||||", "correct": "||||", "concept_id": "math.op.add", "scene": "roman_as_sticks"},
        {"cue": "||| - || = |", "correct": "|", "concept_id": "math.op.sub", "scene": "sticks_sub"},
        {"cue": "III - II = I", "correct": "I", "concept_id": "math.op.sub", "scene": "roman_sub"},
        {"cue": "IV - I = III", "correct": "III", "concept_id": "math.op.sub", "scene": "roman_sub"},
        {"cue": "V - IV = I", "correct": "I", "concept_id": "math.op.sub", "scene": "roman_sub"},
        {"cue": "3 - 2 = 1", "correct": "1", "concept_id": "math.op.sub", "scene": "numeric_sub"},
    ]

    eps = []
    for L in lessons:
        ep = append_episode(
            state,
            cue=L["cue"],
            surface_attempt="?",
            correct=L["correct"],
            lattice_id="schema-math",
            concept_id=L["concept_id"],
            bundle=bundle,
            correction_kind="stick_lesson",
            scene=L["scene"],
        )
        eps.append({**L, "id": ep.get("id")})

    sleep = run_sleep(state, bundle)
    save_runtime_state(store, state)
    state = ensure_prisms(load_field_state(field_state_path(store)))
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])

    def snap(cue: str, expect_op: str | None) -> dict:
        tick = predict_tick(state, cue, modality="schema", expect=expect_op, bundle=bundle)
        pred = tick["predict"]
        return {
            "cue": cue,
            "expect_op": expect_op,
            "verdict": tick["verdict"],
            "hypothesis": pred.get("hypothesis"),
            "unbound": pred.get("unbound_operators"),
            "top4": rank_cue_on_f0(bundle, dec, cue)[:4],
        }

    test_cues: list[tuple[str, str | None]] = [
        ("|| + || = ||||", "math.op.add"),
        ("|| + ||", "math.op.add"),
        ("| + | = ||", "math.op.add"),
        ("| + |", "math.op.add"),
        ("2 + 2 = 4", "math.op.add"),
        ("2 + 2", "math.op.add"),
        ("1 + 1 = 2", "math.op.add"),
        ("I + III = IV", "math.op.add"),
        ("I + III", "math.op.add"),
        ("III - II = I", "math.op.sub"),
        ("III - II", "math.op.sub"),
        ("IV - I = III", "math.op.sub"),
        ("IV - I", "math.op.sub"),
        ("||| - || = |", "math.op.sub"),
        ("3 - 2 = 1", "math.op.sub"),
        ("||||", None),
        ("||", None),
        ("|", None),
        ("IV", None),
        ("I", None),
    ]

    report = {
        "store": store.name,
        "lessons": eps,
        "sleep_merged": sleep.get("merged"),
        "sleep_extracts": [i.get("extract") for i in (sleep.get("items") or []) if i.get("extract")],
        "predict": [snap(c, e) for c, e in test_cues],
        "denotes_edges": [
            e
            for e in dec.get("edges") or []
            if "denotes" in e and any(x in e for x in ("add", "sub", "latn.+", "latn.-"))
        ],
    }

    out = REPO_ROOT / "lab/reports/stick-lesson-series.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
