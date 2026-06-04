#!/usr/bin/env python3
"""Чистый meta size на текстовых карточках: большая / маленькая."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, bootstrap, class_dir_for, cli_pure_meta, import_tools_module

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
_ITEMS = (
    PureMetaPhrase(meta.SIZE_LARGE, "большая", "word-size-large-sans", "size-large"),
    PureMetaPhrase(meta.SIZE_SMALL, "маленькая", "word-size-small-sans", "size-small"),
)


def main() -> None:
    cli_pure_meta(
        LITERACY,
        _ITEMS,
        summary_file="summary-meta-size-pure.json",
        description=__doc__,
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "concepts": [meta.SIZE_LARGE, meta.SIZE_SMALL],
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
