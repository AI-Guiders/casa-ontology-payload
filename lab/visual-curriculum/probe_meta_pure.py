#!/usr/bin/env python3
"""Probe чистых meta-карточек: lang.meta.* по manifest concept_id."""

from __future__ import annotations

from probe_infra import manifest_hints_merged, run_frame_probe

META_PURE_LITERACY_FRAMES = (
    "word-capital-zaglavnaya-bukva-sans",
    "word-capital-verhnego-registra-sans",
    "word-lowercase-strochnaya-bukva-sans",
    "word-lowercase-nizhnego-registra-sans",
    "word-ne_znayu-sans",
    "word-vybor-sans",
    "word-zameshatelstvo-sans",
    "word-size-large-sans",
    "word-size-small-sans",
    "word-bukva-sans",
    "word-slovo-sans",
)

META_PURE_FRAMES = META_PURE_LITERACY_FRAMES


def main() -> None:
    hints = manifest_hints_merged("lessons/literacy-cards")

    def _hint(fid: str) -> str:
        from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

        return canonical_lex_concept_id(hints.get(fid, ""))

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-pure-quiz",
        frames=META_PURE_FRAMES,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename="teacher-meta-pure-quiz.json",
        lock_holder="probe:meta-pure-quiz",
        preds_field="lex_top",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
