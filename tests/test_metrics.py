"""Maturity metric: capability coverage rises as the curriculum closes gaps."""

from __future__ import annotations

import json

from casa.curriculum.loop import mine_targets, run_curriculum
from casa.curriculum.metrics import coverage
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"

PROBES = [
    {"cue": "14", "concept_id": "math.num.fourteen", "lattice_id": "schema-math"},
    {"cue": "11", "concept_id": "math.num.eleven", "lattice_id": "schema-math"},
    {"cue": "13", "concept_id": "math.num.thirteen", "lattice_id": "schema-math"},
]


def _live() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    return state, bundle


def test_coverage_rises_as_curriculum_closes_gaps() -> None:
    state, bundle = _live()
    before = coverage(state, PROBES, bundle=bundle)
    assert before["coverage"] < 1.0  # the field does not know these yet
    assert before["failed"] > 0

    run_curriculum(state, mine_targets(state, PROBES, bundle=bundle), bundle=bundle)

    after = coverage(state, PROBES, bundle=bundle)
    assert after["coverage"] == 1.0
    assert after["gaps"] == []
