"""Deterministic assert-gate for lattice_dan spotlight (CASA-ADR-0010 R4)."""

from __future__ import annotations

import bench_predict_error_v0 as bench
import control_attention_v0 as dan


def test_spotlight_includes_goal_in_universe():
    mask = dan.spotlight(["topic.1.core"], ["topic.1.core", "topic.1.detail", "topic.2.core"])
    assert "topic.1.core" in mask
    assert "topic.2.core" not in mask


def test_apply_mask_is_intersection():
    assert dan.apply_mask(["a", "b", "c"], ["b", "c", "d"]) == {"b", "c"}


def test_sparse_ratio_between_zero_and_one():
    r = dan.sparse_ratio(["a", "b", "c", "d"], ["a"])
    assert 0.0 < r < 1.0


def test_spotlight_walk_sparse_and_predictive():
    report = dan.evaluate_spotlight(bench.synthetic_trajectory())
    assert report["sparse_enough"]
    assert report["still_predictive"]
    assert report["mean_sparse_ratio"] < 0.85
