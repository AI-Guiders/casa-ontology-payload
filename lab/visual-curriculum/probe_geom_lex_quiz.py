#!/usr/bin/env python3
"""Teacher probe: geometry figure → math.geom.* (Russian word on field)."""

from __future__ import annotations

from probe_infra import run_frame_probe

FRAMES = (
    "geom-circle",
    "geom-square",
    "geom-rectangle",
    "geom-stroke",
    "geom-segment",
    "geom-line",
    "geom-circle-center",
    "geom-circle-radius",
)


def main() -> None:
    def _hint(fid: str) -> str:
        from casa.cli.moment_plan import _FRAME_MATH

        row = _FRAME_MATH.get(fid)
        return str(row[2]) if row else ""

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_math import predict_math_for_vis_cue

        return predict_math_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="geom-lex-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-geom-lex-quiz.json",
        lock_holder="probe:geom-lex-quiz",
        preds_field="math_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
