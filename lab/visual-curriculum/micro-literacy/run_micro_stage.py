#!/usr/bin/env python3
"""Run micro-moments for a literacy stage (one vis+lexical → one sleep each)."""

from __future__ import annotations

import argparse
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import steps_for_frame
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", required=True, help="stage id from manifest")
    p.add_argument("--limit", type=int, default=0, help="max frames (0=all)")
    p.add_argument("--offset", type=int, default=0)


def _run(session, args: argparse.Namespace) -> None:
    manifest = session.load_manifest()
    lesson_ids: set[str] = set()
    for st in manifest.get("stages") or []:
        if str(st.get("id")) == args.stage:
            lesson_ids = set(st.get("lesson_ids") or [])
            break
    if not lesson_ids:
        raise SystemExit(f"unknown stage: {args.stage}")

    frames = [f for f in manifest.get("frames") or [] if str(f.get("lesson_id")) in lesson_ids]
    frames.sort(key=lambda f: str(f.get("id")))
    if args.offset:
        frames = frames[args.offset :]
    if args.limit > 0:
        frames = frames[: args.limit]

    session.log({"stage": args.stage, "frames": len(frames)})
    for i, frame in enumerate(frames):
        fid = str(frame.get("id"))
        session.ingest(f"lex-{args.stage}-{fid}"[:80], steps_for_frame(frame), i=i + 1, frame_id=fid)
        if (i + 1) % 10 == 0 or i + 1 == len(frames):
            session.log(session.summary_rows[-1])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    _parser(p)
    args = p.parse_args()
    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file=f"summary-{args.stage}.json",
        summary_builder=lambda s: {"stage": args.stage, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
