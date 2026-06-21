"""General English<->Russian vocabulary curriculum (nouns + adjectives, beyond numbers)."""

from __future__ import annotations

import json

from casa.curriculum import teach, translate_term
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
CURRICULUM = REPO_ROOT / "lab/curriculum/en-vocab-v1.json"


def _taught() -> tuple[dict, dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    cur = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    for lesson in cur["lessons"]:
        teach(
            state,
            concept_id=lesson["concept_id"],
            lattice_id=cur["lattice_id"],
            examples=[{"cue": lesson["en"], "correct": lesson["en"], "scene": f"ru: {lesson['ru']} | en: {lesson['en']}"}],
            bundle=bundle,
        )
    return state, bundle, cur


def test_general_vocabulary_translates_both_ways() -> None:
    state, bundle, cur = _taught()
    for lesson in cur["lessons"]:
        ru, en = lesson["ru"], lesson["en"]
        assert en in translate_term(state, cur["lattice_id"], ru, to_script="latn"), f"RU->EN {ru}"
        assert ru in translate_term(state, cur["lattice_id"], en, to_script="cyrl"), f"EN->RU {en}"
