#!/usr/bin/env python3
"""Lab: reinforce corpus bridge for мама (analytic pilot)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_lab_main

bootstrap(__file__)

_FRAME = "word-d2a8dc30e406-sans"
_LEX = "lang.word.d2a8dc30e406"


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    row = reinforce_vis_lex_bridge(
        session.state,
        frame_id=_FRAME,
        lex_cid=_LEX,
        copies=14,
    )
    session.log(
        {
            "surface": "мама",
            "frame_id": _FRAME,
            "lex_cid": _LEX,
            "reinforced": row is not None,
            "edge": row,
        }
    )


def main() -> None:
    cli_lab_main(
        LITERACY,
        _run,
        summary_file="summary-reinforce-analytic-mama.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
