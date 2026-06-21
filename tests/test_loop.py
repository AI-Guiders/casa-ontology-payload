"""Auto-curriculum loop: mine failures -> draft -> stage -> gate -> promote -> closed."""

from __future__ import annotations

import json

from casa.curriculum.loop import default_generator, mine_targets, run_curriculum
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


def test_mine_finds_gaps_before_teaching() -> None:
    state, bundle = _live()
    targets = mine_targets(state, PROBES, bundle=bundle)
    assert targets, "the field should fail these numerals before being taught"


def test_curriculum_closes_mined_failures() -> None:
    state, bundle = _live()
    targets = mine_targets(state, PROBES, bundle=bundle)
    n = len(targets)
    report = run_curriculum(state, targets, bundle=bundle)
    assert report["n_promoted"] == n
    # re-mine: every gap the curriculum promoted is now closed
    assert mine_targets(state, PROBES, bundle=bundle) == []


def test_generator_is_pluggable() -> None:
    # the generator is the LLM wire-point — a custom one is honored, once per target
    calls: list[str] = []

    def gen(target: dict) -> dict:
        calls.append(str(target["concept_id"]))
        return default_generator(target)

    state, bundle = _live()
    targets = mine_targets(state, PROBES, bundle=bundle)
    run_curriculum(state, targets, generator=gen, bundle=bundle)
    assert calls == [t["concept_id"] for t in targets]
