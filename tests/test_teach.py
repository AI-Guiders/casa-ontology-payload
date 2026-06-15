"""Teaching tool — teach a concept by sanctioned learning, verify recall or held-out."""

from __future__ import annotations

import json
from pathlib import Path

from casa.curriculum.teach import teach
from casa.eval.held_out_gate import GatePolicy
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _state() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    return state, bundle


def test_teach_vocabulary_recall() -> None:
    state, bundle = _state()
    rep = teach(
        state,
        concept_id="math.num.fourteen",
        lattice_id="schema-math",
        examples=[{"cue": "14", "correct": "14"}],
        bundle=bundle,
    )
    assert rep["mode"] == "recall"
    assert rep["learned"] is True
    assert rep["recall"]["14"] is True


def test_teach_no_examples_not_learned() -> None:
    state, bundle = _state()
    # honest reporting: no lesson taught -> not learned (the tool never falsely claims)
    rep = teach(state, concept_id="math.num.six", lattice_id="schema-math", examples=[], bundle=bundle)
    assert rep["learned"] is False


def test_teach_rule_held_out_gate() -> None:
    state, bundle = _state()
    # a generalizing lesson is verified on HELD-OUT cues; policy sets the rigor
    rep = teach(
        state,
        concept_id="math.num.six",
        lattice_id="schema-math",
        examples=[{"cue": c, "correct": c, "scene": "count_row:lab"} for c in ("2", "4", "6")],
        held_out=[{"cue": "6", "target": "6"}],
        bundle=bundle,
        policy=GatePolicy(min_held_out=1, min_passes=1, pass_ratio=1.0),
    )
    assert rep["mode"] == "held_out_gate"
    assert rep["learned"] is True
    assert rep["report"]["held_out_score"] == 1.0
    assert rep["report"]["negative_control_passed"] is True
