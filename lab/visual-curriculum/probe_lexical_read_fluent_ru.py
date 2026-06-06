#!/usr/bin/env python3
"""ADR-0049 L1: held-out corpus whole-word fluent read (offset slice)."""

from __future__ import annotations

import argparse

from probe_infra import manifest_hints, run_frame_probe
from probe_literacy_corpus_quiz import _frames_for_stage


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", default="stage-06-words-cyrl-corpus")
    p.add_argument("--limit", type=int, default=24)
    p.add_argument("--offset", type=int, default=24, help="held-out slice (default skip first 24 train frames)")
    args = p.parse_args()

    frames = _frames_for_stage(args.stage, limit=args.limit, offset=args.offset)
    if not frames:
        raise SystemExit(f"no held-out frames for stage {args.stage!r} offset={args.offset}")

    hints = manifest_hints()

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe="probe_lexical_read_fluent_ru",
        frames=frames,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename="teacher-probe-lexical-read-fluent-ru.json",
        lock_holder="probe:lexical-read-fluent-ru",
        preds_field="lex_top",
        extra_out={"stage": args.stage, "offset": args.offset, "limit": args.limit, "held_out": True},
        print_lines=True,
    )


if __name__ == "__main__":
    main()
