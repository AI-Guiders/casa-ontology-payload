#!/usr/bin/env python3
"""Teacher probe: S4f parallel / perpendicular."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

FRAMES = ("geom-lines-parallel", "geom-lines-perpendicular")


def main() -> None:
    hints = manifest_hints_merged("lessons/visual-cards")

    def _hint(fid: str) -> str:
        from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

        return canonical_lex_concept_id(hints.get(fid, ""))

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-geom-orientation-quiz",
        frames=FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-geom-orientation-quiz.json",
        lock_holder="probe:meta-geom-orientation-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
