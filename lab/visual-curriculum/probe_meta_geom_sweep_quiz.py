#!/usr/bin/env python3
"""Teacher probe: S5s sweep square/rect (math.geom)."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

FRAMES = ("geom-sweep-square-a", "geom-sweep-rect-ab")


def main() -> None:
    hints = manifest_hints_merged("lessons/visual-cards")

    def _hint(fid: str) -> str:
        return hints.get(fid, "")

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_math import predict_math_for_vis_cue

        return predict_math_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-geom-sweep-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-geom-sweep-quiz.json",
        lock_holder="probe:meta-geom-sweep-quiz",
        preds_field="math_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
