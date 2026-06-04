#!/usr/bin/env python3
"""Teacher probe: numberline lengths → math.numberline.length."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

FRAMES = (
    "numberline-length-pure-2",
    "numberline-length-pure-3",
)


def main() -> None:
    hints = manifest_hints_merged("lessons/visual-cards")

    def _hint(fid: str) -> str:
        return hints.get(fid, "math.numberline.length")

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_math import predict_math_for_vis_cue

        return predict_math_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="nline-length-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-nline-length-quiz.json",
        lock_holder="probe:nline-length-quiz",
        preds_field="math_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
