#!/usr/bin/env python3
"""Teacher probe: phonology meta → lang.meta.phonology.vowel / .consonant."""

from __future__ import annotations

import json
from pathlib import Path

from probe_infra import manifest_hints, run_frame_probe

_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "lessons" / "literacy-cards" / "class.manifest.json"
_STAGE = "stage-04-meta-phonology-vowel-consonant"
_PREFIX = "lang.meta.phonology."


def _frames_for_stage(stage_id: str) -> list[str]:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    lesson_ids: set[str] = set()
    for st in manifest.get("stages") or []:
        if str(st.get("id")) == stage_id:
            lesson_ids = set(st.get("lesson_ids") or [])
            break
    if not lesson_ids:
        raise SystemExit(f"unknown stage: {stage_id!r}")
    frames = [
        str(f["id"])
        for f in manifest.get("frames") or []
        if str(f.get("lesson_id")) in lesson_ids
        and str(f.get("concept_id") or "").startswith(_PREFIX)
    ]
    frames.sort()
    return frames


def main() -> None:
    frames = _frames_for_stage(_STAGE)
    if not frames:
        raise SystemExit(
            f"no frames for {_STAGE!r}; run lessons/literacy-cards/tools/build_phonology_meta_cards.py"
        )

    hints = manifest_hints()

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="meta-phonology-quiz",
        frames=frames,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename="teacher-meta-phonology-quiz.json",
        lock_holder="probe:meta-phonology-quiz",
        preds_field="lex_top",
        extra_out={"stage": _STAGE},
        print_lines=True,
    )


if __name__ == "__main__":
    main()
