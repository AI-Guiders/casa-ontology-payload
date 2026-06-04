#!/usr/bin/env python3
"""S4b: meta «длина» на чистых кадрах numberline-length-pure-* (lesson-22)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, VISUAL, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.MEASURE_LENGTH, "длина", "numberline-length-pure-2", "measure-length-pure-2"),
    PureMetaPhrase(meta.MEASURE_LENGTH, "длина", "numberline-length-pure-3", "measure-length-pure-3"),
)


def main() -> None:
    cli_pure_meta(
        VISUAL,
        _ITEMS,
        summary_file="summary-meta-nline-length-pure.json",
        description=__doc__,
        moment_prefix="meta-nline-length-pure",
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "stage": "S4b-meta-measure-length",
            "frames": [i.frame_id for i in _ITEMS],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
