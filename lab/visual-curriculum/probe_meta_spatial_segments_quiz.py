#!/usr/bin/env python3
"""Teacher probe: meta spatial left/right on segments A/B."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

SPATIAL_SEGMENT_FRAMES = (
    "geom-segments-a-left",
    "geom-segments-a-right",
)


def main() -> None:
    hints = manifest_hints_merged("lessons/visual-cards")

    def _hint(fid: str) -> str:
        from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

        return canonical_lex_concept_id(hints.get(fid, ""))

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-spatial-segments-quiz",
        frames=SPATIAL_SEGMENT_FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-spatial-segments-quiz.json",
        lock_holder="probe:meta-spatial-segments-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
