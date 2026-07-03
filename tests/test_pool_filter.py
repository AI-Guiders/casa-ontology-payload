"""Source-quality filter — catches garbled EMEA pairs, keeps clean and lossy-but-valid ones.

The bar is precision: dropping a good pair costs coverage, so every rule targets a concrete
segmentation artifact seen in the real pool (bracket debris, unbalanced parens, a bare-unit
sentence start, a dangling connective tail, run-on instructions).
"""

from __future__ import annotations

from casa.curriculum.pool_filter import filter_pool, pair_reasons


_CLEAN_EN = "The tablet is taken once a day."
_CLEAN_ES = "El comprimido se toma una vez al día."


def _reasons(en=None, es=None):
    # fill the unused side with a clean sentence so a one-sided test doesn't trip «empty»
    return pair_reasons({"id": "x", "en": _CLEAN_EN if en is None else en,
                         "es": _CLEAN_ES if es is None else es})


# --- each rule fires on its artifact --------------------------------------------------------
def test_bracket_debris():
    assert "es:bracket-debris" in _reasons(es="contiene 56,25 mg de ácido ibandrónico,), sal")


def test_unbalanced_parens():
    assert "es:unbalanced-parens" in _reasons(es="menos de 1 mmol (23 mg de sodio por dosis,")


def test_bare_unit_fragment_head():
    assert "en:fragment-head" in _reasons(en="g of granules contains 940 mg of sodium")
    assert "es:fragment-head" in _reasons(es="mg de sacarosa, 1,11 mg de fosfato")


def test_truncated_connective_tail():
    assert "es:truncated-tail" in _reasons(es="Cada comprimido contiene 625 mg de")
    assert "en:truncated-tail" in _reasons(en="notice any side effects not listed in the")


def test_concatenated_instructions():
    r = _reasons(en="Store in a refrigerator Do not freeze Store in the original package")
    assert "en:concatenated-instructions" in r


# --- valid pairs must NOT be dropped (precision) --------------------------------------------
def test_normal_sentence_kept():
    assert _reasons(en="The recommended dose is 10 or 15 mg by mouth per day.",
                    es="La dosis inicial recomendada es de 10 o 15 mg al día.") == []


def test_capitalized_the_is_not_a_fragment():
    # «The …» / «De …» open a normal sentence — the IGNORECASE bug once dropped 3150 of these
    assert _reasons(en="The tablet may be taken with or without food.") == []
    assert _reasons(es="De este modo se evita la contaminación.") == []


def test_single_drug_name_is_not_a_run_on():
    # a capitalized DRUG name mid-sentence is normal, not a concatenation
    assert _reasons(en="Be careful while you are taking Bondenza.") == []


def test_lossy_but_grammatical_pair_kept():
    # «…3 mg de ácido» drops the acid name but stays a complete sentence; its quantity
    # injection is valid, so the pair is kept (not garbled syntax)
    assert _reasons(en="One pre-filled syringe contains 3 mg of ibandronic acid",
                    es="Una jeringa precargada contiene 3 mg de ácido") == []


# --- whole-pool split ------------------------------------------------------------------------
def test_filter_pool_splits_and_tags():
    rows = [
        {"id": "good", "en": "The dose is 5 mg.", "es": "La dosis es de 5 mg."},
        {"id": "bad", "en": "g of granules contains 940 mg", "es": "g de granulado contiene 940 mg"},
    ]
    kept, rejected = filter_pool(rows)
    assert [r["id"] for r in kept] == ["good"]
    assert [r["id"] for r in rejected] == ["bad"]
    assert rejected[0]["_reject"]  # carries reasons
