#!/usr/bin/env python3
"""Метаязык волна 2 — один sleep на карточку; concept_id из meta_concepts.py."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob, jobs_from_steps
from lex_steps import lex_step

_LITERACY = _REPO / "lessons" / "literacy-cards"


def _steps(slug: str, surface: str, concept_id: str) -> list[dict]:
    return [{"visual_frame": f"word-{slug}-sans"}, lex_step(surface, concept_id)]


def main() -> None:
    import sys

    tools = _LITERACY / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    from meta_concepts import WAVE2_CARDS  # noqa: E402

    items = [
        (f"lex-meta2-{slug}"[:80], _steps(slug, surface, concept_id), {"concept_id": concept_id})
        for slug, surface, concept_id in WAVE2_CARDS
    ]
    jobs = jobs_from_steps(items)

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        reports_subdir="micro-literacy",
        extra_sys_paths=(_LITERACY / "tools",),
    )
    def _run(session: CurriculumLabSession) -> None:
        session.log({"words": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(_run, summary_file="summary-meta-language-wave2.json")


if __name__ == "__main__":
    main()
