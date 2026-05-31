"""Control tick extensions — predict / DAN / value (CASA-ADR-0010)."""

from __future__ import annotations

import casa.prisms.control.tick as ct


def test_predict_surprise_on_digest_change() -> None:
    ext = ct.run_control_extensions(
        prior_digest=["topic.0.core"],
        current_digest=["topic.0.core", "unexpected.extra"],
        goal=["topic.0.core"],
        fit_trajectory=[["topic.0.core"], ["topic.1.core"]] * 4,
    )
    assert "unexpected.extra" in ext.surprise


def test_run_control_extensions_contract() -> None:
    ext = ct.run_control_extensions(
        prior_digest=["a"],
        current_digest=["a", "b"],
        goal=["a"],
    )
    d = ext.to_dict()
    assert set(d) == {
        "predicted",
        "surprise",
        "prediction_error",
        "dan_mask",
        "sparse_ratio",
        "masked_digest",
        "value",
    }
    assert 0.0 <= d["prediction_error"] <= 1.0
    assert "b" in d["surprise"]


def test_value_tags_correction_kind() -> None:
    ext = ct.run_control_extensions(
        prior_digest=["x"],
        current_digest=["x"],
        goal=["x"],
        correction_kind="ortho_surface",
    )
    assert ext.value >= 1.0
