#!/usr/bin/env python3
"""Teacher probe: meta «длина» на numberline-length-pure-*."""

from __future__ import annotations

from probe_infra import run_frame_probe

FRAMES = (
    "numberline-length-pure-2",
    "numberline-length-pure-3",
)


def main() -> None:
    hint_id = "lang.meta.measure.length"

    def _hint(_fid: str) -> str:
        return hint_id

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-nline-length-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-nline-length-quiz.json",
        lock_holder="probe:meta-nline-length-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
