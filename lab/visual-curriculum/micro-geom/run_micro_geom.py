#!/usr/bin/env python3
"""Run six geometry-lex micro-moments (one vis+math word per sleep)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_VISUAL = _REPO / "lessons" / "visual-cards"
MICRO = [
    ("geom-micro-circle", "geom-micro-circle.json"),
    ("geom-micro-square", "geom-micro-square.json"),
    ("geom-micro-rectangle", "geom-micro-rectangle.json"),
    ("geom-micro-stroke", "geom-micro-stroke.json"),
    ("geom-micro-segment", "geom-micro-segment.json"),
    ("geom-micro-line", "geom-micro-line.json"),
]


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, MICRO)
    lab = CurriculumLabSession(class_dir=_VISUAL, generated_subdir="micro-geom")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary.json")


if __name__ == "__main__":
    main()
