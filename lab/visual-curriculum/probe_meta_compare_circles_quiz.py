#!/usr/bin/env python3
"""Teacher probe: S6 two circles → lang.meta.compare.greater / .less."""

from __future__ import annotations

from probe_infra import run_frame_probe

FRAMES = (
    "geom-circles-left-greater",
    "geom-circles-left-less",
)


def main() -> None:
    def _hint(fid: str) -> str:
        from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

        if fid == "geom-circles-left-greater":
            return canonical_lex_concept_id("lang.meta.compare.greater")
        if fid == "geom-circles-left-less":
            return canonical_lex_concept_id("lang.meta.compare.less")
        return ""

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-compare-circles-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-compare-circles-quiz.json",
        lock_holder="probe:meta-compare-circles-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
