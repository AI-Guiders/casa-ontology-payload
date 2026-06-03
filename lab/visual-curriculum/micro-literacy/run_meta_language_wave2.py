#!/usr/bin/env python3
"""Метаязык волна 2 — один sleep на карточку; concept_id из meta_concepts.py."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import (
    LITERACY,
    bootstrap,
    class_dir_for,
    cli_run_jobs,
    import_tools_module,
    jobs_meta_phrase_vis,
)

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")


def main() -> None:
    cli_run_jobs(
        LITERACY,
        lambda: jobs_meta_phrase_vis(meta.WAVE2_CARDS),
        summary_file="summary-meta-language-wave2.json",
        description=__doc__,
        log_start={"words": len(meta.WAVE2_CARDS)},
    )


if __name__ == "__main__":
    main()
