#!/usr/bin/env python3
"""Lab: reinforce category cards гласная / согласная (empty + ambiguous on probe)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_lab_main

bootstrap(__file__)

_PAIRS = (
    ("meta-phonology-vowel-sans", "lang.meta.phonology.vowel", "гласная"),
    ("meta-phonology-consonant-sans", "lang.meta.phonology.consonant", "согласная"),
)


def _run(session, _args) -> None:
    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    for frame_id, lex_cid, label in _PAIRS:
        row = reinforce_vis_lex_bridge(
            session.state,
            frame_id=frame_id,
            lex_cid=lex_cid,
            copies=14,
        )
        session.log(
            {
                "surface": label,
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
        summary_file="summary-reinforce-phonology-meta-category.json",
        description=__doc__,
    )


if __name__ == "__main__":
    main()
