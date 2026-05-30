#!/usr/bin/env python3
"""Compare Exp J train/bench artifacts (grammar monolithic full vs union windowed)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _mix_from_score(score: dict) -> float | None:
    if not score:
        return None
    c = score.get("concepts", {}).get("f1")
    e = score.get("edges", {}).get("f1")
    if c is None or e is None:
        return None
    return float(c) * 0.6 + float(e) * 0.4


def _row(label: str, obj: dict | None, keys: list[str]) -> dict:
    out: dict = {"label": label, "present": obj is not None}
    if obj is None:
        return out
    for k in keys:
        if k in obj:
            out[k] = obj[k]
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, default=Path("examples/exp_j_ru_v1/compare_grammar_full_vs_union_windowed.json"))
    args = p.parse_args()
    root = args.root
    rep = root / "examples/exp_j_ru_v1"

    grammar_train = _read(root / "examples/nca_out_exp_j_ru_grammar_full_v1/report.json")
    union_windowed_train = _read(root / "examples/nca_out_exp_j_ru_union_windowed_v1/report.json")
    union_mono_train = _read(root / "examples/nca_out_exp_j_ru_union_full_v1/report.json")

    grammar_curve = _read(rep / "curve_grammar_s20.json")
    union_windowed_curve = _read(rep / "curve_union_windowed_s20.json")
    union_mono_curve = _read(rep / "curve_union_s20.json")

    grammar_repair = _read(rep / "report_repair_grammar.json")
    union_windowed_repair = _read(rep / "report_repair_union_windowed.json")

    windowed_bench = _read(rep / "report_windowed_repair_union.json")

    def train_summary(tag: str, rep_obj: dict | None) -> dict:
        if not rep_obj:
            return {"tag": tag, "present": False}
        reports = rep_obj.get("reports") or []
        mix = rep_obj.get("best_mix")
        if mix is None and reports:
            s0 = reports[0].get("score", {})
            mix = _mix_from_score(s0)
        return {
            "tag": tag,
            "present": True,
            "train_mode": rep_obj.get("train_mode"),
            "epochs": rep_obj.get("epochs"),
            "token_count_union": rep_obj.get("token_count_union"),
            "windows_per_batch": rep_obj.get("windows_per_batch"),
            "best_mix": mix,
        }

    def curve_summary(curve: dict | None) -> dict | None:
        if not curve:
            return None
        pts = curve.get("points") or curve.get("rows") or curve.get("results") or []
        if not pts:
            return {"present": True, "points": 0}
        # last damage point mix if available
        last = pts[-1] if isinstance(pts, list) else None
        mix = None
        if isinstance(last, dict):
            sc = last.get("score") or last
            mix = _mix_from_score(sc) if isinstance(sc, dict) else last.get("mix")
        return {"present": True, "points": len(pts), "last_mix": mix}

    out = {
        "schema_version": 1,
        "train": [
            train_summary("grammar_full_monolithic", grammar_train),
            train_summary("union_windowed_batched", union_windowed_train),
            train_summary("union_full_monolithic", union_mono_train),
        ],
        "curve": {
            "grammar_full": curve_summary(grammar_curve),
            "union_windowed": curve_summary(union_windowed_curve),
            "union_monolithic": curve_summary(union_mono_curve),
        },
        "answer_repair": {
            "grammar_full": _row(
                "grammar_full",
                grammar_repair,
                ["answer_at_1_field", "answer_at_1_repair", "scored_queries"],
            ),
            "union_windowed": _row(
                "union_windowed",
                union_windowed_repair,
                ["answer_at_1_field", "answer_at_1_repair", "scored_queries"],
            ),
        },
        "windowed_repair_bench": windowed_bench,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
