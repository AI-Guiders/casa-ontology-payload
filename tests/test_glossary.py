"""Bulk bilingual glossary: a large word list loaded in ONE sleep, all translatable.

teach() runs a sleep per concept; teach_glossary appends every pair first and runs
a single consolidation sleep. This is the scale path — a large open RU<->EN list
(NOT the proprietary Oxford dictionary) becomes a deterministic glossary at once.
"""

from __future__ import annotations

import json

import pytest

from casa.curriculum import load_pairs, teach_glossary, translate_term
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
GLOSSARY = REPO_ROOT / "lab/curriculum/en-glossary-v1.json"
OPEN_DICT = REPO_ROOT / "lab/curriculum/en-glossary-ru-open.json"
LATTICE = "schema-math"
# CI loads a capped slice of the open dictionary — the full 32k loads the same way
# in one sleep but takes minutes (the names mint is superlinear in lattice size),
# which is too slow for CI. Real bulk loads run it once, offline.
OPEN_DICT_CI_CAP = 1500


def _taught() -> tuple[dict, dict, list[tuple[str, str]]]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    pairs = load_pairs(GLOSSARY)
    teach_glossary(state, pairs, lattice_id=LATTICE, bundle=bundle)
    return state, bundle, pairs


def test_whole_glossary_taught_in_one_sleep_translates_both_ways() -> None:
    state, bundle, pairs = _taught()
    for ru, en in pairs:
        assert en in translate_term(state, LATTICE, ru, to_script="latn"), f"RU->EN {ru}"
        assert ru in translate_term(state, LATTICE, en, to_script="cyrl"), f"EN->RU {en}"


def test_load_pairs_reads_the_sample_glossary() -> None:
    pairs = load_pairs(GLOSSARY)
    assert len(pairs) >= 40
    assert ("кот", "cat") in pairs


@pytest.mark.skipif(not OPEN_DICT.exists(), reason="open dictionary not present")
def test_open_dictionary_slice_loads_and_translates() -> None:
    # a real open RU<->EN dictionary (OpenRussian.org, ~32k pairs) loaded at scale;
    # CI exercises a capped slice, every pair translatable RU->EN after one sleep
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    pairs = load_pairs(OPEN_DICT)[:OPEN_DICT_CI_CAP]
    assert len(pairs) >= 1000, "open dictionary should be large"
    teach_glossary(state, pairs, lattice_id=LATTICE, bundle=bundle)
    ok = sum(1 for ru, en in pairs if en in translate_term(state, LATTICE, ru, to_script="latn"))
    assert ok == len(pairs), f"only {ok}/{len(pairs)} open-dict pairs translate RU->EN"
