#!/usr/bin/env python3
"""Teacher probe: corpus word frames → lang.word.* (manifest concept_id)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import manifest_hints, run_frame_probe

_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "lessons" / "literacy-cards" / "class.manifest.json"


def _frames_for_stage(
    stage_id: str,
    *,
    limit: int,
    offset: int,
) -> list[str]:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    lesson_ids: set[str] = set()
    for st in manifest.get("stages") or []:
        if str(st.get("id")) == stage_id:
            lesson_ids = set(st.get("lesson_ids") or [])
            break
    if not lesson_ids:
        raise SystemExit(f"unknown stage: {stage_id!r}")
    frames = [f for f in manifest.get("frames") or [] if str(f.get("lesson_id")) in lesson_ids]
    frames.sort(key=lambda f: str(f.get("id")))
    if offset:
        frames = frames[offset:]
    if limit > 0:
        frames = frames[:limit]
    return [str(f["id"]) for f in frames]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", default="stage-06-words-cyrl-corpus")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--offset", type=int, default=0)
    args = p.parse_args()

    frames = _frames_for_stage(args.stage, limit=args.limit, offset=args.offset)
    if not frames:
        raise SystemExit(f"no frames for stage {args.stage!r}")

    hints = manifest_hints()

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="literacy-corpus-quiz",
        frames=frames,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename="teacher-literacy-corpus-quiz.json",
        lock_holder="probe:literacy-corpus-quiz",
        preds_field="lex_top",
        extra_out={"stage": args.stage, "offset": args.offset, "limit": args.limit},
        print_lines=True,
    )


if __name__ == "__main__":
    main()
