#!/usr/bin/env python3
"""Literacy pilot: а/А + мама/кот/дом (отдельный sleep на moment)."""

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
    ("lex-micro-word-mama", "lex-micro-word-mama.json"),
    ("lex-micro-word-kot", "lex-micro-word-kot.json"),
    ("lex-micro-word-dom", "lex-micro-word-dom.json"),
]


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, MICRO)
    lab = CurriculumLabSession(class_dir=_LITERACY, generated_subdir="micro-literacy")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-pilot-literacy-start.json")


if __name__ == "__main__":
    main()
