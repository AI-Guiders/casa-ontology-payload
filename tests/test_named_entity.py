"""Opaque named entities — drug names as parse-time nodes + the entity divergence class.

Drug names are an open class no ontology can enumerate. On declared-language sides an
unknown CAPITALIZED token (mid-sentence or ALL-CAPS), or the substance right after
«measure + of/de», becomes ``concept.named:{normalized}`` with a fixed implicit type.
Identity = the normalized name, so a swapped drug between translation sides is an
ENTITY-class divergence — the fourth dangerous class. Normalization is heuristic
(final-vowel strip + double-letter collapse for INN variants) and honestly scoped.
"""

from __future__ import annotations

import pytest

from casa.curriculum.equivalence import check_equivalence
from casa.curriculum.parse import _normalize_name, parse_fingerprint, parse_graph
from casa.curriculum.world import build_meaning_state


@pytest.fixture(scope="module")
def world():
    state, lat = build_meaning_state()
    return state, lat


def _key(state, lat, text, lang=None):
    return parse_fingerprint(state, lat, text, lang=lang)["key"]


# --- name normalization (INN cross-lingual variants) -----------------------------------
@pytest.mark.parametrize("a,b", [
    ("aripiprazole", "aripiprazol"),   # EN final -e
    ("amoxicillin", "amoxicilina"),    # double letter + ES final -a
    ("ibuprofen", "ibuprofeno"),       # ES final -o
    ("ABILIFY", "Abilify"),            # case only
])
def test_name_normalization_matches(a, b):
    assert _normalize_name(a) == _normalize_name(b)


# --- parsing with named entities ---------------------------------------------------------
def test_allcaps_drug_parses(world):
    state, lat = world
    g = parse_graph(state, lat, "no tome ABILIFY", lang="es")
    sat = [(e["rel"], e["dst"]) for e in g["edges"] if e.get("satisfied")]
    assert ("take", "concept.named:abilify") in sat
    assert all(e["polarity"] == "neg" for e in g["edges"])


def test_substance_after_measure_partitive(world):
    state, lat = world
    # lowercase INN after «measure + de» — the partitive position identifies the substance,
    # and the measure binds to IT: contains(vial, aripiprazol{9.75mg})
    g = parse_graph(state, lat, "Un vial contiene 9,75 mg de aripiprazol", lang="es")
    sat = {(e["rel"], e["src"], e["dst"]) for e in g["edges"] if e.get("satisfied")}
    assert ("contains", "concept.vial", "concept.named:aripiprazol") in sat
    node = g["nodes"]["concept.named:aripiprazol"]
    assert node["measure"] == {"value": 9.75, "unit": "mg"}


def test_cross_lingual_same_drug_equivalent(world):
    state, lat = world
    r = check_equivalence(state, lat,
                          "the vial contains 9.75 mg of aripiprazole",
                          "el vial contiene 9,75 mg de aripiprazol", langs=("en", "es"))
    assert r["verdict"] == "equivalent"


def test_swapped_drug_is_entity(world):
    state, lat = world
    r = check_equivalence(state, lat, "do not take TAMIFLU", "no tome ABILIFY", langs=("en", "es"))
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "entity" for d in r["divergences"])


def test_same_drug_dose_swap_still_quantity(world):
    state, lat = world
    r = check_equivalence(state, lat,
                          "the vial contains 9.75 mg of aripiprazole",
                          "el vial contiene 97,5 mg de aripiprazol", langs=("en", "es"))
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "quantity" for d in r["divergences"])


# --- guards ------------------------------------------------------------------------------
def test_no_named_entities_without_declared_lang(world):
    state, lat = world  # the RU/EN default path must not invent nodes
    g = parse_graph(state, lat, "не принимай АБИЛИФАЙ")
    assert not any(str(cid).startswith("concept.named:") for cid in g["nodes"])


def test_sentence_initial_titlecase_not_named(world):
    state, lat = world  # ordinary sentence capitalization must not become an entity
    g = parse_graph(state, lat, "Take the tablet", lang="en")
    assert not any(str(cid).startswith("concept.named:") for cid in g["nodes"])
