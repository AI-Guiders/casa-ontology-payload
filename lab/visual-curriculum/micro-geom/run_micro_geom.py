#!/usr/bin/env python3
"""Run six geometry-lex micro-moments (one vis+math word per sleep)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("geom-micro-circle", "geom-micro-circle.json"),
    ("geom-micro-square", "geom-micro-square.json"),
    ("geom-micro-rectangle", "geom-micro-rectangle.json"),
    ("geom-micro-stroke", "geom-micro-stroke.json"),
    ("geom-micro-segment", "geom-micro-segment.json"),
    ("geom-micro-line", "geom-micro-line.json"),
]


def main() -> None:
    cli_json_batch(VISUAL, _STEPS, MICRO, summary_file="summary.json", description=__doc__)


if __name__ == "__main__":
    main()
