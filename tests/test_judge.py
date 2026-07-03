"""Judge pipeline — protocol parsing, mock end-to-end run, metric arithmetic.

The pipeline must be exercisable with zero network: the mock provider produces
deterministic verdicts, so a full run → aggregate → metrics pass is a plain unit test.
"""

from __future__ import annotations

import json

import pytest

from casa.curriculum.judge import _parse_reply, load_benchmark, run_judge
from casa.curriculum.judge_metrics import _aggregate, evaluate, load_judgments, results_table

BENCH = [
    {"id": "b1", "src_lang": "en", "tgt_lang": "es", "src": "Do not take X.", "tgt": "Tome X.",
     "label": "error", "error_class": "polarity", "injection": {}, "source": "emea",
     "split": "public", "kernel_parseable": True, "generator": "t"},
    {"id": "b2", "src_lang": "en", "tgt_lang": "es", "src": "The dose is 75 mg.",
     "tgt": "La dosis es de 75 mg.", "label": "equivalent", "error_class": None,
     "injection": None, "source": "emea", "split": "public", "kernel_parseable": True,
     "generator": "t"},
    {"id": "b3", "src_lang": "en", "tgt_lang": "es", "src": "The dose is 75 mg.",
     "tgt": "La dosis es de 75 ml.", "label": "error", "error_class": "unit",
     "injection": {}, "source": "emea", "split": "heldout", "kernel_parseable": True,
     "generator": "t"},
]


# --- reply parsing -------------------------------------------------------------------------
def test_parse_reply_strict_json():
    r = _parse_reply('{"verdict": "error", "error_class": "unit", "confidence": 0.9}')
    assert r == {"verdict": "error", "error_class": "unit", "confidence": 0.9}


def test_parse_reply_json_inside_prose():
    r = _parse_reply('Sure! Here is my answer:\n{"verdict": "equivalent", "error_class": null, "confidence": 0.8}')
    assert r["verdict"] == "equivalent" and r["error_class"] is None


def test_parse_reply_garbage_is_invalid_not_guessed():
    assert _parse_reply("I think it's fine")["verdict"] == "invalid"
    assert _parse_reply('{"verdict": "maybe"}')["verdict"] == "invalid"


def test_parse_reply_unknown_class_becomes_other():
    r = _parse_reply('{"verdict": "error", "error_class": "spelling", "confidence": 2.5}')
    assert r["error_class"] == "other" and r["confidence"] == 1.0


# --- mock run + metrics --------------------------------------------------------------------
@pytest.fixture()
def bench_file(tmp_path):
    p = tmp_path / "bench.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in BENCH), encoding="utf-8")
    return p


def test_load_benchmark_splits(bench_file):
    assert {r["id"] for r in load_benchmark(bench_file)} == {"b1", "b2"}
    assert len(load_benchmark(bench_file, split="all")) == 3
    assert len(load_benchmark(bench_file, split="all", limit=1)) == 1


def _records_sans_timing(paths):
    out = []
    for p in paths:
        for ln in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            r.pop("latency_ms", None)  # wall-clock — the only nondeterministic field
            out.append(r)
    return out


def test_mock_run_is_deterministic_and_resumable(bench_file, tmp_path):
    rows = load_benchmark(bench_file, split="all")
    d1, d2 = tmp_path / "j1", tmp_path / "j2"
    p1 = run_judge(rows, provider="mock", model="m", runs=3, out_dir=d1)
    p2 = run_judge(rows, provider="mock", model="m", runs=3, out_dir=d2)
    assert _records_sans_timing(p1) == _records_sans_timing(p2)
    # resume: re-running over the same dir must not duplicate records
    run_judge(rows, provider="mock", model="m", runs=3, out_dir=d1)
    assert _records_sans_timing(p1) == _records_sans_timing(p2)


def test_metrics_arithmetic_on_known_verdicts():
    # hand-built verdicts: b1 caught 3/3 runs, b2 false-alarmed 1/3, b3 missed 2/3
    def rec(i, run, verdict, klass=None, conf=0.9):
        return {"id": i, "run": run, "model": "m", "prompt_version": "p",
                "verdict": verdict, "error_class": klass, "confidence": conf,
                "latency_ms": 10, "tokens_in": 5, "tokens_out": 5}

    judged = {
        "b1": [rec("b1", k, "error", "polarity") for k in range(3)],
        "b2": [rec("b2", 0, "error", "other"), rec("b2", 1, "equivalent"), rec("b2", 2, "equivalent")],
        "b3": [rec("b3", 0, "error", "unit"), rec("b3", 1, "equivalent"), rec("b3", 2, "equivalent")],
    }
    m = evaluate(BENCH, judged)
    assert m["items"] == 3 and m["answered"] == 1.0
    assert m["recall"] == 0.5  # b1 caught, b3 missed by majority
    assert m["fpr"] == 0.0  # b2 majority is equivalent
    assert m["per_class"]["polarity"]["recall"] == 1.0
    assert m["per_class"]["polarity"]["exact_class"] == 1.0
    assert m["per_class"]["unit"]["recall"] == 0.0
    assert m["consistency"]["unanimous"] == pytest.approx(1 / 3, abs=1e-4)
    # risk–coverage: full coverage exists, risk there = 1/3 wrong (b3)
    full = [pt for pt in m["risk_coverage"] if pt["coverage"] == 1.0]
    assert full and full[0]["risk"] == pytest.approx(1 / 3, abs=1e-4)


def test_aggregate_tie_breaks_toward_error():
    def rec(verdict, klass=None):
        return {"verdict": verdict, "error_class": klass, "confidence": 0.5}

    a = _aggregate([rec("error", "unit"), rec("equivalent")])
    assert a["verdict"] == "error" and a["margin"] == 0.0


def test_aggregate_all_invalid_is_abstention():
    a = _aggregate([{"verdict": "invalid", "error_class": None, "confidence": 0.0}])
    assert a["verdict"] == "abstain"


def test_end_to_end_mock_table(bench_file, tmp_path):
    rows = load_benchmark(bench_file, split="all")
    paths = run_judge(rows, provider="mock", model="mock-1", runs=5, out_dir=tmp_path / "j")
    groups = load_judgments(paths)
    results = {model: evaluate(rows, judged) for (model, _), judged in groups.items()}
    table = results_table(results)
    assert "mock-1" in table and table.count("|") > 20
    m = results["mock-1"]
    assert m["runs"] == 5 and m["items"] == 3
    assert m["cost"]["mean_latency_ms"] >= 0
