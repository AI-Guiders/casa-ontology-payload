"""Emergent add↔mul↔cardinality extract from co-presented mul: scenes."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_equiv_extract import parse_equivalence_magnitudes
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa.prisms.tick.predict_tick import predict_tick

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"

BRIDGE = [
    ("2+2=4", "4", "math.num.four", "mul: дважды по два"),
    ("2*2=4", "4", "math.op.mul", "mul: дважды по два"),
    ("2+2+2=6", "6", "math.num.six", "mul: трижды по два"),
    ("2*3=6", "6", "math.op.mul", "mul: трижды по два"),
    ("2+2+2 = 2*3 = 6", "6", "math.num.six", "mul: add=mul same scene"),
    ("2+2 = 2*2 = 4", "4", "math.num.four", "mul: add=mul same scene"),
]


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def test_parse_equivalence_magnitudes() -> None:
    assert parse_equivalence_magnitudes("2+2+2 = 2*3 = 6") == 6
    assert parse_equivalence_magnitudes("2+2 = 2*2 = 4") == 4


def test_sleep_extract_enables_equiv_predict() -> None:
    b = _bundle()
    state = ensure_prisms({})
    ingest_math_bundle(state, b)
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
            structure_tag="self_promote",  # sanctioned earned-write (gate-authorized in production)
        )
    sleep = run_sleep(state, b)
    kinds = [it.get("kind") for it in sleep.get("items") or []]
    assert "emergent_mul_equiv" in kinds

    for cue, expect in (
        ("2+2+2 = 2*3 = 6", "math.num.six"),
        ("2+2 = 2*2 = 4", "math.num.four"),
        ("2+2+2=6", "math.num.six"),
        ("2+2=4", "math.num.four"),
        ("2*3=6", "math.num.six"),
        ("3*3=?", "math.num.nine"),
    ):
        tick = predict_tick(state, cue, modality="schema", bundle=b)
        hyp = (tick.get("predict") or {}).get("hypothesis")
        assert hyp == expect, f"{cue!r} → {hyp!r}, expected {expect!r}"
