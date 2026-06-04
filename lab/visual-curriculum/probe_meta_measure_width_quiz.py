#!/usr/bin/env python3
"""Teacher probe: S5 meta width."""

from __future__ import annotations

from probe_infra import run_frame_probe

FRAMES = ("geom-rectangle-width",)


def main() -> None:
    hint_id = "lang.meta.measure.width"

    def _hint(_fid: str) -> str:
        return hint_id

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-measure-width-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-measure-width-quiz.json",
        lock_holder="probe:meta-measure-width-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
