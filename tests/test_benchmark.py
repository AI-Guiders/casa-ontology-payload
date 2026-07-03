"""NUN-Bench generator — determinism, per-class injector correctness, metadata replay.

The whole point of the generator is auditability: no randomness (hash-keyed choices, same
input → byte-identical benchmark) and full reproducibility (applying ``replacement`` at
``char_span`` to the clean side must reproduce the corrupted side exactly).
"""

from __future__ import annotations

import json

import pytest

from casa.curriculum.benchmark import (
    _canaries,
    build_benchmark,
    inject_entity,
    inject_polarity,
    inject_quantity,
    inject_unit,
)

POOL = [
    {"id": "p1", "en": "Do not take TAMIFLU if you are pregnant.",
     "es": "No tome TAMIFLU si está embarazada.", "tags": ["negation"]},
    {"id": "p2", "en": "The dose is 75 mg once a day.",
     "es": "La dosis es de 75 mg una vez al día.", "tags": ["dose"]},
    {"id": "p3", "en": "The vial contains 9.75 mg of aripiprazole.",
     "es": "El vial contiene 9,75 mg de aripiprazol.", "tags": ["dose"]},
    {"id": "p4", "en": "Store the tablets in the carton.",
     "es": "Conserve los comprimidos en el envase.", "tags": ["instruction"]},
    {"id": "p5", "en": "Do not use ABILIFY without asking your doctor.",
     "es": "No use ABILIFY sin consultar a su médico.", "tags": ["negation"]},
]


def _replay(clean: str, meta: dict) -> str:
    a, b = meta["char_span"]
    return clean[:a] + meta["replacement"] + clean[b:]


# --- injectors ---------------------------------------------------------------------------
def test_polarity_drop_and_capitalization():
    text = "No tome TAMIFLU si está embarazada."
    out, meta = inject_polarity(text, "es", "k")
    assert out.startswith("Tome TAMIFLU")
    assert meta["class"] == "polarity"
    assert _replay(text, meta) == out  # capitalization is part of the replacement


def test_polarity_mid_sentence_drop_replays():
    text = "El comprimido no debe tomarse con alimentos."
    out, meta = inject_polarity(text, "es", "k")
    assert " no " not in f" {out} "
    assert _replay(text, meta) == out


def test_polarity_skips_negative_concord():
    # dropping «no» would leave «ningún» — not a clean flip, must be skipped
    assert inject_polarity("No utilice ningún resto de la jeringa.", "es", "k") is None


def test_polarity_skips_double_negation():
    # two negations in two clauses — dropping one does not flip the sentence
    assert inject_polarity("Los niños no deben tomar esto y no debe darse a adultos.", "es", "k") is None


def test_quantity_changes_value():
    text = "La dosis es de 75 mg."
    out, meta = inject_quantity(text, "es", "k")
    assert meta["original"] == "75" and meta["replacement"] != "75"
    assert _replay(text, meta) == out


def test_quantity_decimal_stays_decimalish():
    text = "El vial contiene 9,75 mg."
    out, meta = inject_quantity(text, "es", "k2")
    assert meta["original"] == "9,75"
    assert out != text and _replay(text, meta) == out


def test_quantity_transposition_never_leads_with_zero():
    # «250» → «052» reads as a typo, not a different dose — must fall back to digit replace
    for key in ("k", "k1", "k2", "k3", "k4", "k5", "k6", "k7"):
        res = inject_quantity("La dosis es de 250 mg.", "es", key)
        assert res is not None
        assert not res[1]["replacement"].startswith("0")


def test_quantity_decimal_shift_strips_uncovered_zeros():
    for key in ("k", "k1", "k2", "k3", "k4", "k5", "k6", "k7"):
        res = inject_quantity("Jeringa precargada de 0,5 ml.", "es", key)
        assert res is not None
        rep = res[1]["replacement"]
        assert not (len(rep) > 1 and rep[0] == "0" and rep[1] not in ",.")


def test_quantity_skips_trailing_section_number():
    # leaflet section header — the bare trailing number is a TOC index, not a dose
    assert inject_quantity("Antes de tomar Dafiro 3.", "es", "k") is None
    assert inject_quantity("Antes de usar Aldurazyme 30", "es", "k") is None


def test_quantity_skips_leading_section_number():
    assert inject_quantity("3. Cómo tomar Neupro", "es", "k") is None


def test_quantity_still_injects_real_doses():
    assert inject_quantity("La dosis es de 75 mg una vez al día.", "es", "k") is not None


def test_unit_swap():
    text = "La dosis es de 75 mg."
    out, meta = inject_unit(text, "es", "k")
    assert meta["original"] == "mg" and meta["replacement"] in {"ml"}
    assert "75 ml" in out


def test_entity_swap_keeps_style_and_differs():
    text = "No tome TAMIFLU si está embarazada."
    out, meta = inject_entity(text, "es", "k")
    assert meta["original"] == "TAMIFLU"
    assert meta["replacement"].isupper() and meta["replacement"] != "TAMIFLU"
    assert _replay(text, meta) == out


def test_entity_requires_a_name():
    assert inject_entity("la dosis es de 75 mg.", "es", "k") is None


# --- assembly ----------------------------------------------------------------------------
@pytest.fixture()
def pool_file(tmp_path):
    p = tmp_path / "pool.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in POOL), encoding="utf-8")
    return p


def test_build_is_deterministic(pool_file, tmp_path):
    o1, o2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    s1 = build_benchmark(pool_file, o1, per_class=1, controls=2)
    s2 = build_benchmark(pool_file, o2, per_class=1, controls=2)
    assert s1 == s2
    assert o1.read_text(encoding="utf-8") == o2.read_text(encoding="utf-8")


def test_build_rows_replay_and_split(pool_file, tmp_path):
    out = tmp_path / "bench.jsonl"
    stats = build_benchmark(pool_file, out, per_class=1, controls=2)
    rows = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines()]
    assert stats["errors"] >= 3  # at least polarity/quantity/unit/entity minus unapplicable
    by_id = {r["id"]: r for r in rows}
    pool_by_id = {r["id"]: r for r in POOL}
    for r in rows:
        if r["label"] == "error" and r["source"] == "emea":
            clean = pool_by_id[r["id"].split("#")[0]]["es"]
            assert _replay(clean, r["injection"]) == r["tgt"]
        if r["source"] == "canary":
            assert r["split"] == "heldout"
    assert any(r["split"] == "heldout" for r in rows)


def test_canaries_are_invented_names():
    rows = _canaries()
    assert all(r["split"] == "heldout" for r in rows)
    assert any(r["label"] == "error" for r in rows) and any(r["label"] == "equivalent" for r in rows)
