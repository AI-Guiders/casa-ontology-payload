"""Gate for bench_retention (CASA-ADR-0009 UC v0.3)."""

from __future__ import annotations

import casa.cli.bench.bench_retention as br


def test_replay_beats_ablation_on_synthetic_scenario() -> None:
    report = br.compare(interference_words=28, rehearsal_sleeps=2)
    assert report["ablation"]["immediate_pass"]
    assert report["improved"]
    assert report["replay"]["final_copies"] >= report["ablation"]["final_copies"]
