#!/usr/bin/env python3
"""Contrast pass: круг ↔ квадрат — чередование, каждый шаг свой sleep (без cartesian batch)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_VISUAL = _REPO / "lessons" / "visual-cards"
MICRO = [
    ("geom-micro-square-r7", "geom-micro-square.json"),
]


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, MICRO)
    lab = CurriculumLabSession(class_dir=_VISUAL, reports_subdir="micro-geom")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-round-square-contrast.json")


if __name__ == "__main__":
    main()
