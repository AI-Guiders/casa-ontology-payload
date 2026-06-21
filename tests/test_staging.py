"""Staging: candidate applied in isolation, promoted to live only on a passing gate."""

from __future__ import annotations

import json

from casa.curriculum.staging import stage_and_promote
from casa.eval.held_out_gate import ablate_injection_vectors, score_case
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _live() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    return state, bundle


def _surfaces(state: dict, cue: str, concept_id: str, bundle: dict) -> bool:
    return bool(
        score_case(
            ablate_injection_vectors(state),
            {"lattice": "schema-math", "cue": cue, "concept_id": concept_id, "target": cue},
            bundle=bundle,
        )["pass"]
    )


def test_staging_promotes_passing_lesson() -> None:
    live, bundle = _live()
    lesson = {"concept_id": "math.num.fourteen", "lattice_id": "schema-math", "examples": [{"cue": "14", "correct": "14"}]}
    out = stage_and_promote(live, lesson, bundle=bundle)
    assert out["promoted"] is True
    # the live field now actually knows it
    assert _surfaces(live, "14", "math.num.fourteen", bundle) is True


def test_staging_isolates_failed_candidate() -> None:
    live, bundle = _live()
    before = _surfaces(live, "14", "math.num.fourteen", bundle)
    # a held-out lesson with too few probes fails the default gate -> rejected
    lesson = {
        "concept_id": "math.num.fourteen",
        "lattice_id": "schema-math",
        "examples": [{"cue": "14", "correct": "14"}],
        "held_out": [{"cue": "14", "target": "14"}],  # 1 cue < default min_held_out=4 -> not learned
    }
    out = stage_and_promote(live, lesson, bundle=bundle)
    assert out["promoted"] is False
    # the candidate touched only the discarded copy — live is unchanged
    assert _surfaces(live, "14", "math.num.fourteen", bundle) == before
