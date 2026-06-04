#!/usr/bin/env python3
"""Lab: reinforce closed-class tail (им empty, она ambiguous with им)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_lab_main

bootstrap(__file__)

_PAIRS = (
    ("word-0d3963c6db63-sans", "lang.word.0d3963c6db63", "им"),
    ("word-0e338553d71f-sans", "lang.word.0e338553d71f", "она"),
)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    for frame_id, lex_cid, label in _PAIRS:
        row = reinforce_vis_lex_bridge(
            session.state,
            frame_id=frame_id,
            lex_cid=lex_cid,
            copies=12,
        )
        session.log(
            {
                "word": label,
                "frame_id": frame_id,
                "lex_cid": lex_cid,
                "reinforced": row is not None,
                "edge": row,
            }
        )


def main() -> None:
    cli_lab_main(
        LITERACY,
        _run,
        summary_file="summary-reinforce-literacy-closed-class-tail.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
