"""Bootstrap CI — point estimates match the metrics, intervals bracket them, seed is stable."""

from __future__ import annotations

from casa.curriculum.judge_ci import _metrics, _percentile, bootstrap_ci

TRUTH = [
    {"id": "e1", "label": "error", "error_class": "polarity"},
    {"id": "e2", "label": "error", "error_class": "unit"},
    {"id": "c1", "label": "equivalent", "error_class": None},
    {"id": "c2", "label": "equivalent", "error_class": None},
]


def _rec(i, verdict, klass=None, conf=0.9):
    return {"id": i, "run": 0, "model": "m", "prompt_version": "p",
            "verdict": verdict, "error_class": klass, "confidence": conf}


def test_percentile_basic():
    xs = [0.0, 0.25, 0.5, 0.75, 1.0]
    assert _percentile(xs, 0.5) == 0.5
    assert _percentile(xs, 0.0) == 0.0
    assert _percentile(xs, 1.0) == 1.0


def test_metrics_point_values():
    items = [
        {"id": "e1", "is_error": True, "answered": True, "says_error": True, "correct": True,
         "margin": 1.0, "confidence": 0.9},
        {"id": "e2", "is_error": True, "answered": True, "says_error": False, "correct": False,
         "margin": 0.2, "confidence": 0.5},
        {"id": "c1", "is_error": False, "answered": True, "says_error": False, "correct": True,
         "margin": 1.0, "confidence": 0.9},
        {"id": "c2", "is_error": False, "answered": True, "says_error": True, "correct": False,
         "margin": 0.6, "confidence": 0.7},
    ]
    m = _metrics(items)
    assert m["recall"] == 0.5          # 1 of 2 errors caught
    assert m["fpr"] == 0.5             # 1 of 2 controls false-alarmed
    assert m["answered"] == 1.0
    # margin-desc order: e1(1.0,correct), c1(1.0,correct), c2(0.6,WRONG) → prefix of 2 correct
    assert m["zero_risk_coverage"] == 0.5


def test_bootstrap_point_matches_and_brackets():
    judged = {
        "e1": [_rec("e1", "error", "polarity")],
        "e2": [_rec("e2", "error", "unit")],
        "c1": [_rec("c1", "equivalent")],
        "c2": [_rec("c2", "error", "other")],  # a false alarm
    }
    ci = bootstrap_ci(TRUTH, judged, n_boot=500)
    assert ci["recall"]["point"] == 1.0
    assert ci["fpr"]["point"] == 0.5
    # CI must bracket the point estimate
    for k in ("recall", "fpr", "precision", "zero_risk_coverage"):
        assert ci[k]["lo"] <= ci[k]["point"] <= ci[k]["hi"]


def test_bootstrap_is_seed_deterministic():
    judged = {r["id"]: [_rec(r["id"], "error" if r["label"] == "error" else "equivalent",
                             r["error_class"])] for r in TRUTH}
    a = bootstrap_ci(TRUTH, judged, n_boot=300, seed=1)
    b = bootstrap_ci(TRUTH, judged, n_boot=300, seed=1)
    assert a == b
