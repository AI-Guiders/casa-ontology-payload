#!/usr/bin/env python3
"""Contrast pass: а ↔ А — чередование register, отдельный sleep на каждую пару (без cartesian batch)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_LITERACY = _REPO / "lessons" / "literacy-cards"
ROUNDS = 8


def _schedule() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for r in range(1, ROUNDS + 1):
        out.append((f"lex-micro-a-contrast-r{r}-lower", "lex-micro-a-lower.json"))
        out.append((f"lex-micro-a-contrast-r{r}-upper", "lex-micro-a-upper.json"))
    return out


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, _schedule())
    lab = CurriculumLabSession(class_dir=_LITERACY, reports_subdir="micro-literacy")
    def _run(session: CurriculumLabSession) -> None:
        session.log({"rounds": ROUNDS, "moments": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(_run, summary_file="summary-a-register-contrast.json")


if __name__ == "__main__":
    main()
