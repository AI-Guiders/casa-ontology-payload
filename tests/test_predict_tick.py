"""Deterministic assert-gate for lattice_predict digest forward-model (CASA-ADR-0010 R3)."""

from __future__ import annotations

import bench_predict_error_v0 as bench
import predict_tick_v0 as pt


def test_fit_and_predict_next_simple():
    traj = [["a"], ["b"], ["c"], ["a"], ["b"], ["c"]]
    model = pt.fit_transitions(traj)
    assert pt.predict_next(["a"], model) == {"b"}
    assert pt.predict_next(["b"], model) == {"c"}
    assert pt.predict_next(["c"], model) == {"a"}


def test_predict_next_unknown_concept_is_empty():
    model = pt.fit_transitions([["a"], ["b"]])
    assert pt.predict_next(["zzz"], model) == set()


def test_persistence_baseline_repeats_current():
    assert pt.predict_persistence(["x", "y"]) == {"x", "y"}


def test_f1_and_error_edges():
    assert pt.f1(set(), set()) == 1.0
    assert pt.prediction_error({"a"}, {"a"}) == 0.0
    assert pt.prediction_error({"a"}, {"b"}) == 1.0


def test_surprise_is_unexpected_observed():
    assert pt.surprise({"a"}, {"a", "b"}) == {"b"}
    assert pt.surprise({"a", "b"}, {"a"}) == set()


def test_rollout_multi_step():
    model = pt.fit_transitions([["a"], ["b"], ["c"], ["a"], ["b"], ["c"]])
    assert pt.rollout(["a"], model, steps=2) == {"c"}


def test_predict_beats_persistence_on_walk():
    report = bench.run(bench.synthetic_trajectory(), train_frac=0.7, top=1)
    assert report["improved"]
    assert report["predict_mean_error"] < report["baseline_mean_error"]
    assert report["predict_mean_error"] < 0.5
