#!/usr/bin/env python3
"""Score Kolb cycle report: all 4 phases present and AE pass rate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def score_kolb(report: dict) -> dict:
    ce = report.get("concrete_experience") or {}
    ro = report.get("reflective_observation") or {}
    ac = report.get("abstract_conceptualization") or {}
    ae = report.get("active_experimentation") or {}

    phases_ok = all(
        [
            bool(ce.get("attempt")),
            bool(ro.get("observations")),
            ac.get("applied") is not None or ac.get("note"),
            ae.get("total", 0) > 0,
        ]
    )
    return {
        "phases_complete": phases_ok,
        "ce_attempt": ce.get("attempt"),
        "ro_needs_teacher": ro.get("needs_teacher"),
        "ac_applied": ac.get("applied"),
        "ae_passed": ae.get("passed"),
        "ae_total": ae.get("total"),
        "ae_pass_rate": ae.get("pass_rate"),
        "kolb_ok": phases_ok and float(ae.get("pass_rate") or 0) >= 0.6,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    print(json.dumps(score_kolb(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
