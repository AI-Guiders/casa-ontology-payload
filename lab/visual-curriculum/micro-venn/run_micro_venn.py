#!/usr/bin/env python3
"""Run five Venn micro-moments (one vis+math per sleep)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import VENN, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("venn-micro-intersect", "venn-micro-intersect.json"),
    ("venn-micro-union", "venn-micro-union.json"),
    ("venn-micro-subset", "venn-micro-subset.json"),
    ("venn-micro-disjoint", "venn-micro-disjoint.json"),
    ("venn-micro-a-only", "venn-micro-a-only.json"),
]


def main() -> None:
    cli_json_batch(VENN, _STEPS, MICRO, summary_file="summary.json", description=__doc__)


if __name__ == "__main__":
    main()
