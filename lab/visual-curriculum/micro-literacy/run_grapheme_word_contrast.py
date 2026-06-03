#!/usr/bin/env python3
"""Contrast pass: буква ↔ слово — чередование granule, отдельный sleep на каждую пару."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_LITERACY = _REPO / "lessons" / "literacy-cards"
ROUND_STEPS = (
    ("lex-granule-letter-a-lower.json", "letter"),
    ("lex-granule-word-mama.json", "word"),
    ("lex-granule-letter-a-upper.json", "letter"),
    ("lex-granule-word-kot.json", "word"),
)
ROUNDS = 3


def _schedule() -> list[tuple[str, str, dict]]:
    out: list[tuple[str, str, dict]] = []
    for r in range(1, ROUNDS + 1):
        for steps_file, granule in ROUND_STEPS:
            stem = steps_file.replace(".json", "").replace("lex-granule-", "")
            out.append((f"lex-granule-contrast-r{r}-{stem}"[:80], steps_file, {"granule": granule}))
    return out


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, _schedule())
    lab = CurriculumLabSession(class_dir=_LITERACY, reports_subdir="micro-literacy")
    def _run(session: CurriculumLabSession) -> None:
        session.log({"rounds": ROUNDS, "moments": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(
        _run,
        summary_file="summary-grapheme-word-contrast.json",
        summary_builder=lambda s: {"rounds": ROUNDS, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
