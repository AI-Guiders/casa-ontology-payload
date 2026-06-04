#!/usr/bin/env python3
"""Бинарный vis-контраст: geom-circle-large ↔ geom-circle-small + meta size."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from curriculum_lab import IngestJob
from runner_infra import LITERACY, VISUAL, bootstrap, class_dir_for, cli_rounds_modes_jobs, import_tools_module, lex_step

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_PAIRS = (
    ("geom-circle-large", meta.SIZE_LARGE, "большая", "large"),
    ("geom-circle-small", meta.SIZE_SMALL, "маленькая", "small"),
)


def _jobs(rounds: int, modes: tuple[str, ...]) -> list[IngestJob]:
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for frame_id, concept_id, surface, tag in _PAIRS:
            if "phrase_vis" in modes:
                jobs.append(
                    IngestJob(
                        f"geom-size-contrast-{tag}-vis-r{r}",
                        [{"visual_frame": frame_id}, lex_step(surface, concept_id)],
                        {"mode": "phrase_vis", "scale": tag},
                    )
                )
            if "lex_only" in modes:
                jobs.append(
                    IngestJob(
                        f"geom-size-contrast-{tag}-lex-r{r}",
                        [lex_step(surface, concept_id)],
                        {"mode": "lex_only", "scale": tag},
                    )
                )
    return jobs


def main() -> None:
    cli_rounds_modes_jobs(
        VISUAL,
        _jobs,
        summary_file="summary-meta-size-geom-contrast.json",
        description=__doc__,
        default_rounds=4,
        default_modes=["phrase_vis"],
    )


if __name__ == "__main__":
    main()
