#!/usr/bin/env python3
"""Чистый мета «не знаю»: lex_only и phrase_vis, без кадров букв."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, PureMetaPhrase, bootstrap, cli_pure_meta

bootstrap(__file__)
_ITEM = PureMetaPhrase(
    "lang.meta.epistemic.unknown",
    "не знаю",
    "word-ne_znayu-sans",
    "epistemic-unknown",
)


def main() -> None:
    cli_pure_meta(
        LITERACY,
        [_ITEM],
        summary_file="summary-meta-ne-znayu-pure.json",
        description=__doc__,
        default_rounds=6,
        log_start=lambda rounds, modes, jobs: {
            "concept": _ITEM.concept_id,
            "modes": list(modes),
            "rounds": rounds,
            "moments": len(jobs),
        },
    )


if __name__ == "__main__":
    main()
