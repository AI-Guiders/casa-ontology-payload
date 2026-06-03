#!/usr/bin/env python3
"""Пилот метаязыка (text tract): буква, слово, заглавная, строчная — по одному sleep на слово."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_LITERACY = _REPO / "lessons" / "literacy-cards"
MICRO = [
    ("lex-meta-bukva", "lex-meta-bukva.json"),
    ("lex-meta-slovo", "lex-meta-slovo.json"),
    ("lex-meta-zaglavnaya", "lex-meta-zaglavnaya.json"),
    ("lex-meta-strochnaya", "lex-meta-strochnaya.json"),
]


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, MICRO)
    lab = CurriculumLabSession(class_dir=_LITERACY, reports_subdir="micro-literacy")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-meta-language.json")


if __name__ == "__main__":
    main()
