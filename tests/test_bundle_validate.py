"""validate_bundle — pre-write gate for the KB write-target."""

from __future__ import annotations

from casa.prisms.shared.bundle_validate import WriteCaps, validate_bundle


def _codes(rep) -> set[str]:
    return {v["code"] for v in rep["violations"]}


def test_valid_bundle_passes() -> None:
    bundle = {
        "claims": [
            {"concept_id": "ru.dialog.greeting", "text": "hi", "slots": {"bind_boost": "ru.dialog.greeting:30|ru.dialog.self:12"}},
            {"concept_id": "ru.dialog.thanks", "text": "ok", "slots": {}},
            {"concept_id": "ru.prop.bare"},  # bare prefix in a weighted slot is fine
        ]
    }
    rep = validate_bundle(bundle)
    assert rep["ok"] is True
    assert rep["violations"] == []
    assert rep["claim_count"] == 3


def test_bundle_not_dict_and_claims_not_list() -> None:
    assert validate_bundle("nope")["ok"] is False
    assert "bundle_not_dict" in _codes(validate_bundle("nope"))
    assert "claims_not_list" in _codes(validate_bundle({"claims": "x"}))


def test_malformed_weighted_prefixes_are_rejected() -> None:
    # the exact silent-corruption cases the runtime parser mis-handles
    bundle = {
        "claims": [
            {"concept_id": "a", "slots": {"bind_boost": ":5"}},          # empty prefix -> matches all
            {"concept_id": "b", "slots": {"bind_boost": "hub:5:7"}},     # multi-colon mis-split
            {"concept_id": "c", "slots": {"bind_boost": "hub:abc"}},     # non-int weight (silently dropped)
            {"concept_id": "d", "slots": {"bind_demote": "hub:-3"}},     # negative weight inverts
        ]
    }
    rep = validate_bundle(bundle)
    assert rep["ok"] is False
    codes = _codes(rep)
    assert "empty_prefix" in codes
    assert "multi_colon_prefix" in codes
    assert "non_int_weight" in codes
    assert "negative_weight" in codes


def test_weight_over_cap_rejected() -> None:
    bundle = {"claims": [{"concept_id": "a", "slots": {"bind_boost": "hub:9999"}}]}
    rep = validate_bundle(bundle, caps=WriteCaps(max_weight=60))
    assert rep["ok"] is False
    assert "weight_over_cap" in _codes(rep)


def test_duplicate_concept_id_rejected() -> None:
    bundle = {"claims": [{"concept_id": "dup"}, {"concept_id": "dup"}]}
    rep = validate_bundle(bundle)
    assert rep["ok"] is False
    assert "duplicate_concept_id" in _codes(rep)


def test_structural_violations() -> None:
    bundle = {
        "claims": [
            "not-a-dict",
            {"concept_id": ""},                       # empty concept_id
            {"concept_id": 123},                      # non-str concept_id
            {"concept_id": "ok", "text": 5},          # non-str text
            {"concept_id": "ok2", "slots": "nope"},   # non-dict slots
        ]
    }
    rep = validate_bundle(bundle)
    assert rep["ok"] is False
    codes = _codes(rep)
    assert "claim_not_dict" in codes
    assert "bad_concept_id" in codes
    assert "bad_text" in codes
    assert "bad_slots" in codes


def test_too_many_claims_rejected() -> None:
    bundle = {"claims": [{"concept_id": f"c{i}"} for i in range(11)]}
    rep = validate_bundle(bundle, caps=WriteCaps(max_claims=10))
    assert rep["ok"] is False
    assert "too_many_claims" in _codes(rep)


def test_collision_with_live_is_warn_not_error() -> None:
    bundle = {"claims": [{"concept_id": "ru.dialog.greeting"}]}
    rep = validate_bundle(bundle, live_concept_ids={"ru.dialog.greeting"})
    # collision is reported but does not fail the bundle (intentional updates allowed)
    assert rep["ok"] is True
    assert "concept_id_collision" in _codes(rep)
    assert all(v["severity"] == "warn" for v in rep["violations"])
