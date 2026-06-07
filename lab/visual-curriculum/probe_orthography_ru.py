#!/usr/bin/env python3
"""Block 10 — orthography in context (B8, ADR-0049 L3)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_CURRICULUM = Path(__file__).resolve().parent
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from text_kb_probe import run_text_kb_probe  # noqa: E402

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/ortho-moment-plan-v1.json"
_PROBE = "probe_orthography_ru"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()
    report = run_text_kb_probe(
        probe_id=_PROBE,
        plan_path=args.plan,
        report_filename="teacher-probe-orthography-ru.json",
        store_id=args.store,
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
