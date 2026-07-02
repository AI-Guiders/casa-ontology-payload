"""Medical-label domain pack + the measure-claim form — the EMEA benchmark vocabulary.

Pins: the pack's concepts resolve in all three languages; «contains» is a container claim
(not agent ownership); the trailing measure «the dose is 75 mg» parses as num_eq into the
value-mutex machinery; the dangerous classes stay caught on medical forms cross-lingually.
"""

from __future__ import annotations

import pytest

from casa.curriculum.equivalence import check_equivalence
from casa.curriculum.parse import parse_fingerprint, parse_graph
from casa.curriculum.world import build_meaning_state


@pytest.fixture(scope="module")
def world():
    state, lat = build_meaning_state()
    return state, lat


def _key(state, lat, text, lang=None):
    return parse_fingerprint(state, lat, text, lang=lang)["key"]


def _rels(state, lat, text, lang=None):
    return {e["rel"] for e in parse_graph(state, lat, text, lang=lang)["edges"] if e.get("satisfied")}


# --- the measure-claim form («the dose is 75 mg») --------------------------------------
@pytest.mark.parametrize("text,lang", [
    ("the dose is 75 mg", None),
    ("доза 75 мг", None),
    ("la dosis es de 75 mg", "es"),
])
def test_measure_claim_parses_as_num_eq(world, text, lang):
    state, lat = world
    assert "num_eq" in _rels(state, lat, text, lang=lang)


def test_measure_claim_cross_lingual_identity(world):
    state, lat = world
    en = _key(state, lat, "the dose is 75 mg")
    assert en == _key(state, lat, "la dosis es de 75 mg", lang="es")
    assert en == _key(state, lat, "доза 75 мг")


def test_contains_is_container_claim(world):
    state, lat = world
    assert "contains" in _rels(state, lat, "el comprimido contiene lactosa", lang="es")
    assert _key(state, lat, "el comprimido contiene lactosa", lang="es") == \
        _key(state, lat, "the tablet contains lactose")


def test_contains_trailing_measure(world):
    state, lat = world
    # «el vial contiene 3 ml» — no object noun, the amount IS the claim
    assert "num_eq" in _rels(state, lat, "el vial contiene 3 ml", lang="es")
    assert _key(state, lat, "el vial contiene 3 ml", lang="es") == \
        _key(state, lat, "the vial contains 3 ml")


# --- dangerous classes on medical forms -------------------------------------------------
def test_dose_swap_is_quantity(world):
    state, lat = world
    r = check_equivalence(state, lat, "the dose is 75 mg", "la dosis es de 50 mg", langs=("en", "es"))
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "quantity" for d in r["divergences"])


def test_unit_swap_mg_mcg(world):
    state, lat = world
    r = check_equivalence(state, lat, "the dose is 75 mg", "la dosis es de 75 µg", langs=("en", "es"))
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "unit" for d in r["divergences"])


def test_negated_instruction_medicine(world):
    state, lat = world
    r = check_equivalence(state, lat, "do not take this medicine", "no tome este medicamento",
                          langs=("en", "es"))
    assert r["verdict"] == "equivalent"
    r2 = check_equivalence(state, lat, "do not take this medicine", "tome este medicamento",
                           langs=("en", "es"))
    assert r2["verdict"] == "divergent"
    assert any(d["class"] == "polarity" for d in r2["divergences"])


def test_store_imperative(world):
    state, lat = world
    assert "store" in _rels(state, lat, "store the tablets")
    assert _key(state, lat, "conserve los comprimidos", lang="es") == \
        _key(state, lat, "store the tablets")


def test_ru_medical_names_resolve(world):
    state, lat = world  # trilingual: the RU side of the pack works too
    assert _key(state, lat, "храни таблетку в холодильнике") == \
        _key(state, lat, "conserve el comprimido en la nevera", lang="es")


# --- tokenization hazards of real label text --------------------------------------------
def test_decimal_dose_one_number(world):
    state, lat = world
    # «9,75 mg» must stay ONE number — 9.75, not 75 (comma-decimal, the dose hazard)
    g = parse_graph(state, lat, "el vial contiene 9,75 mg", lang="es")
    amount = g["nodes"]["concept.amount"]["measure"]
    assert amount == {"value": 9.75, "unit": "mg"}
    assert _key(state, lat, "el vial contiene 9,75 mg", lang="es") == \
        _key(state, lat, "the vial contains 9.75 mg")


def test_decimal_differs_from_integer(world):
    state, lat = world
    assert _key(state, lat, "the dose is 9.75 mg") != _key(state, lat, "the dose is 975 mg")


def test_temporal_noun_does_not_capture_measure(world):
    state, lat = world
    # «15 mg once a day» — the amount belongs to the dose, never to the day
    g = parse_graph(state, lat, "the usual dose is 15 mg once a day")
    assert g["nodes"]["concept.amount"]["measure"] == {"value": 15, "unit": "mg"}
    assert _key(state, lat, "the usual dose is 15 mg once a day") == \
        _key(state, lat, "the dose is 15 mg")


def test_glued_unit_splits(world):
    state, lat = world
    assert _key(state, lat, "la dosis es de 2ml", lang="es") == \
        _key(state, lat, "the dose is 2 ml")
