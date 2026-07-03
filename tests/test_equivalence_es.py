"""Cross-lingual EN↔ES equivalence triage — the benchmark's core path.

The validator receives a pair with DECLARED side languages (an EMEA row knows which side
is English and which Spanish): ``check_equivalence(..., langs=("en", "es"))``. The tests
pin the dangerous-class kernel across the EN↔ES boundary: polarity (dropped «no»),
quantity (2↔3), unit (ml↔mg) — plus honest ❓ when a side does not parse.
"""

from __future__ import annotations

import pytest

from casa.curriculum.equivalence import check_equivalence
from casa.curriculum.world import build_meaning_state


@pytest.fixture(scope="module")
def world():
    state, lat = build_meaning_state()
    return state, lat


def _check(world, en, es):
    state, lat = world
    return check_equivalence(state, lat, en, es, langs=("en", "es"))


def test_equivalent_cross_lingual(world):
    r = _check(world, "the apple is on the table", "la manzana en la mesa")
    assert r["verdict"] == "equivalent"


def test_equivalent_negated_both_sides(world):
    # correctly negating translation is NOT a divergence
    r = _check(world, "do not open the file", "no abra el archivo")
    assert r["verdict"] == "equivalent"


def test_dropped_negation_is_polarity(world):
    r = _check(world, "do not open the file", "abra el archivo")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "polarity" for d in r["divergences"])


def test_swapped_count_is_quantity(world):
    r = _check(world, "two apples on the table", "tres manzanas en la mesa")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "quantity" for d in r["divergences"])


def test_swapped_unit_is_unit(world):
    r = _check(world, "5 ml of water on the table", "5 mg de agua en la mesa")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "unit" for d in r["divergences"])


def test_unparsed_side_is_uncheckable(world):
    r = _check(world, "the apple is on the table", "frase sin estructura reconocible")
    assert r["verdict"] == "uncheckable"


def test_unbound_digit_mismatch_is_divergent_not_equivalent(world):
    # the parser drops the step index — the guard must still see 7 vs 8 in the raw text
    r = _check(world, "the apple is on the table 7.", "la manzana en la mesa 8.")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "quantity" for d in r["divergences"])


def test_unbound_equal_digits_downgrade_to_uncheckable(world):
    # graphs agree and the digits match, but their roles were never verified — no claim
    r = _check(world, "the apple is on the table 7.", "la manzana en la mesa 7.")
    assert r["verdict"] == "uncheckable"


def test_bound_digits_still_equivalent(world):
    # when every digit is IN the graph (a measure), the guard stays silent
    r = _check(world, "5 ml of water on the table", "5 ml de agua en la mesa")
    assert r["verdict"] == "equivalent"


def test_lexical_unit_mismatch_flagged_without_graph_help(world):
    r = _check(world, "the apple is on the table 5 mg.", "la manzana en la mesa 5 ml.")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "unit" for d in r["divergences"])


def test_decimal_comma_vs_dot_is_not_a_divergence(world):
    # EN «0.05» and ES «0,05» are the same number — formats must not false-alarm
    r = _check(world, "the apple is on the table 0.05.", "la manzana en la mesa 0,05.")
    assert r["verdict"] == "uncheckable"  # equal but unbound — honest abstention, no alarm


def test_sin_participle_does_not_mask_dropped_negation(world):
    # «sin abrir» is a modifier, not clause negation: with «no» dropped the sides must
    # NOT come back equivalent (this exact pair once false-passed)
    r = _check(world, "The unopened bottle does not require any special storage conditions.",
               "El frasco sin abrir requiere condiciones especiales de conservación.")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "polarity" for d in r["divergences"])


def test_temporal_count_does_not_overwrite_dose(world):
    # «150 mg. una vez al día» — the «una» belongs to «vez», never to the dose
    r = _check(world, "The usual recommended dose is 150 mg once a day.",
               "La dosis habitual recomendada es de 150 mg. una vez al día.")
    assert r["verdict"] == "equivalent"


def test_swapped_name_in_unparsed_modifier_blocks_equivalence(world):
    # the drug hides in a modifier the graph drops («Aldara cream» → cream) — a swap
    # must never yield «equivalent»; abstention is the honest floor
    r = _check(world, "Do not use Aldara cream for the treatment.",
               "No utilice Abilify crema para el tratamiento.")
    assert r["verdict"] != "equivalent"


def test_structure_only_mismatch_abstains(world):
    # partial parses that do not align are a parse gap as often as a meaning gap
    r = _check(world, "Keep the pen cap on in order to protect from light.",
               "Conservar siempre en el embalaje exterior para proteger la insulina de la luz.")
    assert r["verdict"] == "uncheckable"


def test_package_carton_are_one_concept(world):
    r = _check(world, "Store in the original package.", "Conservar en el embalaje original.")
    assert r["verdict"] == "equivalent"
    r2 = _check(world, "Store in the original package.", "Conservar en el envase original.")
    assert r2["verdict"] == "equivalent"


def test_ablation_none_confirms_where_full_abstains(world):
    # a number the graph never bound (a trailing bare digit): «full» abstains via the
    # residual guard (uncheckable), «none» has no guard and confirms — the ablation that
    # shows the guards change the verdict (and, on real corrupted pairs, cause false passes)
    state, lat = world
    full = check_equivalence(state, lat, "the apple is on the table 7.",
                             "la manzana en la mesa 7.", langs=("en", "es"), guards="full")
    none = check_equivalence(state, lat, "the apple is on the table 7.",
                             "la manzana en la mesa 7.", langs=("en", "es"), guards="none")
    assert full["verdict"] == "uncheckable"  # guarded: number outside the graph is unverified
    assert none["verdict"] == "equivalent"   # unguarded: confirms on the matching graph alone


def test_ablation_lexical_catches_unit_misses_polarity(world):
    state, lat = world
    # lexical baseline catches a unit swap (mg→ml changes the surface)
    unit = check_equivalence(state, lat, "the dose is 75 mg", "la dosis es de 75 ml",
                             langs=("en", "es"), guards="lexical")
    assert unit["verdict"] == "divergent"
    # but is BLIND to a dropped negation (no number/name changes) — the graph's job
    pol = check_equivalence(state, lat, "do not use Abseamed", "use Abseamed",
                            langs=("en", "es"), guards="lexical")
    assert pol["verdict"] == "equivalent"  # lexical miss — full kernel catches it as polarity


def test_langs_omitted_backward_compatible(world):
    state, lat = world  # old two-argument-style call still works (RU↔EN path untouched)
    r = check_equivalence(state, lat, "яблоко на столе", "the apple is on the table")
    assert r["verdict"] == "equivalent"
