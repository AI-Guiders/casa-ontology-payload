#!/usr/bin/env python3
"""Teacher probe: meta compare greater/less (nline + two circles)."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

META_COMPARE_FRAMES = (
    "numberline-compare-3gt2",
    "numberline-compare-2lt3",
    "geom-circles-left-greater",
    "geom-circles-left-less",
)

# nline frames: manifest concept_id = math.compare.*; meta hint — override
_META_HINT_OVERRIDE = {
    "numberline-compare-3gt2": "lang.meta.compare.greater",
    "numberline-compare-2lt3": "lang.meta.compare.less",
}


def main() -> None:
    hints = manifest_hints_merged("lessons/visual-cards")

    def _hint(fid: str) -> str:
        from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

        raw = _META_HINT_OVERRIDE.get(fid) or hints.get(fid, "")
        return canonical_lex_concept_id(raw)

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-compare-quiz",
        frames=META_COMPARE_FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-compare-quiz.json",
        lock_holder="probe:meta-compare-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
