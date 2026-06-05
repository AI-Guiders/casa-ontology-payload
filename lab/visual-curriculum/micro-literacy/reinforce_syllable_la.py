#!/usr/bin/env python3
"""Lab: reinforce syllable.ла on syllable-ла-sans (phrase pilot B2 tie-break)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_lab_main

bootstrap(__file__)

_FRAME = "syllable-ла-sans"
_LEX = "syllable.ла"


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    row = reinforce_vis_lex_bridge(
        session.state,
        frame_id=_FRAME,
        lex_cid=_LEX,
        copies=18,
    )
    session.log(
        {
            "surface": "ла",
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
        summary_file="summary-reinforce-syllable-la.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
