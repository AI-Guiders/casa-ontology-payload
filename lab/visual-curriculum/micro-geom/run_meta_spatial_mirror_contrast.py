#!/usr/bin/env python3
"""Contrast: левее↔правее, выше↔ниже — canon → mirror → mirror (extra sleep на зеркало)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from curriculum_lab import IngestJob
from runner_infra import LITERACY, VISUAL, bootstrap, class_dir_for, cli_rounds_modes_jobs, import_tools_module, lex_step

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")

_LR = (
    ("left", "geom-segments-a-left", meta.SPATIAL_LEFT_OF, "левее"),
    ("right", "geom-segments-a-right", meta.SPATIAL_RIGHT_OF, "правее"),
)
_AB = (
    ("above", "geom-segments-a-above", meta.SPATIAL_ABOVE_OF, "выше"),
    ("below", "geom-segments-a-below", meta.SPATIAL_BELOW_OF, "ниже"),
)


def _phrase_vis(tag: str, frame_id: str, concept_id: str, surface: str, *, r: int, axis: str) -> IngestJob:
    return IngestJob(
        f"meta-spatial-{axis}-contrast-{tag}-r{r}"[:80],
        [{"visual_frame": frame_id}, lex_step(surface, concept_id)],
        {"mode": "phrase_vis", "axis": axis, "tag": tag},
    )


def _axis_round_jobs(axis: str, pairs: tuple[tuple[str, str, str, str], ...], *, r: int) -> list[IngestJob]:
    canon, mirror = pairs
    return [
        _phrase_vis(canon[0], canon[1], canon[2], canon[3], r=r, axis=axis),
        _phrase_vis(mirror[0], mirror[1], mirror[2], mirror[3], r=r, axis=axis),
        _phrase_vis(mirror[0], mirror[1], mirror[2], mirror[3], r=r, axis=axis),
    ]


def _jobs(rounds: int, modes: tuple[str, ...]) -> list[IngestJob]:
    if "phrase_vis" not in modes:
        return []
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        jobs.extend(_axis_round_jobs("lr", _LR, r=r))
        jobs.extend(_axis_round_jobs("ab", _AB, r=r))
    return jobs


def main() -> None:
    cli_rounds_modes_jobs(
        VISUAL,
        _jobs,
        summary_file="summary-meta-spatial-mirror-contrast.json",
        description=__doc__,
        default_rounds=8,
        default_modes=["phrase_vis"],
        log_start=lambda rounds, modes, jobs: {
            "stage": "S3-spatial-mirror-contrast",
            "pattern": "canon,mirror,mirror",
            "axes": ["lr", "ab"],
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
