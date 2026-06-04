#!/usr/bin/env python3
"""S5s: sweep — vis-only segment/translate, затем math square/rect (каждый свой sleep)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("geom-sweep-segment-vis", "geom-sweep-segment-vis.json"),
    ("geom-sweep-translate-vis", "geom-sweep-translate-vis.json"),
    ("geom-sweep-square", "geom-sweep-square.json"),
    ("geom-sweep-rect", "geom-sweep-rect.json"),
]


def main() -> None:
    cli_json_batch(
        VISUAL,
        _STEPS,
        MICRO,
        summary_file="summary-meta-geom-sweep.json",
        description=__doc__,
        log_start={"stage": "S5s-geom-sweep", "moments": len(MICRO)},
    )


if __name__ == "__main__":
    main()
