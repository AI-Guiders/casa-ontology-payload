#!/usr/bin/env python3
"""Run micro-moments for a literacy stage (one vis+lexical → one sleep each)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import steps_for_frame
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
_CURRICULUM = _MICRO.parent
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from literacy_pedagogy import default_wordlist_for_stage, frames_for_stage  # noqa: E402


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", required=True, help="stage id from manifest")
    p.add_argument("--limit", type=int, default=0, help="max frames (0=all)")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument(
        "--order",
        choices=("wordlist", "frame_id", "manifest"),
        default="frame_id",
        help="wordlist — порядок ru-*-wordlist.txt (рекомендуется closed-class)",
    )
    p.add_argument("--wordlist", type=Path, default=None)


def _run(session, args: argparse.Namespace) -> None:
    manifest = session.load_manifest()
    wordlist = args.wordlist
    if wordlist is None and args.order == "wordlist":
        wordlist = default_wordlist_for_stage(args.stage)

    frames = frames_for_stage(
        manifest,
        args.stage,
        limit=args.limit,
        offset=args.offset,
        order=args.order,
        wordlist_path=wordlist,
    )

    session.log({"stage": args.stage, "frames": len(frames), "order": args.order})
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
