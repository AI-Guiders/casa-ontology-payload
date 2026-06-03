#!/usr/bin/env python3
"""Pilot: а / А — два micro-moment (отдельный sleep каждый)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_LITERACY = _REPO / "lessons" / "literacy-cards"
MICRO = [
    ("lex-micro-a-lower", "lex-micro-a-lower.json"),
    ("lex-micro-a-upper", "lex-micro-a-upper.json"),
]


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, MICRO)
    lab = CurriculumLabSession(class_dir=_LITERACY, reports_subdir="micro-literacy")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-pilot-a.json")


if __name__ == "__main__":
    main()
