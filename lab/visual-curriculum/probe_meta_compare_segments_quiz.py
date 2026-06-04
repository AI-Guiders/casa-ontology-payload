#!/usr/bin/env python3
"""Teacher probe: meta compare on segments A/B (равны / длиннее / короче)."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

SEGMENT_COMPARE_FRAMES = (
    "geom-segments-equal",
    "geom-segments-a-longer",
    "geom-segments-a-shorter",
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
        probe="meta-compare-segments-quiz",
        frames=SEGMENT_COMPARE_FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-compare-segments-quiz.json",
        lock_holder="probe:meta-compare-segments-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
