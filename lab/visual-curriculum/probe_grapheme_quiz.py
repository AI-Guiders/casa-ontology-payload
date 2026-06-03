#!/usr/bin/env python3
"""Teacher probe: letter frame → grapheme.cyrl.* (register from manifest concept_id)."""

from __future__ import annotations

from probe_infra import manifest_hints, run_frame_probe

PILOT_FRAMES = (
    "letter-a-lower-sans",
    "letter-a-upper-sans",
    "word-mama-sans",
    "word-kot-sans",
    "word-dom-sans",
)


def main() -> None:
    hints = manifest_hints()

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="literacy-quiz",
        frames=PILOT_FRAMES,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename="teacher-grapheme-quiz.json",
        lock_holder="probe:grapheme-quiz",
        preds_field="lex_top",
    )


if __name__ == "__main__":
    main()
