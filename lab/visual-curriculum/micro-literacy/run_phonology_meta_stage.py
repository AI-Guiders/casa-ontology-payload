#!/usr/bin/env python3
"""Ingest stage-04 phonology meta (order from ru-phonology-ingest-order-v1.txt)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import steps_for_frame
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
_CURRICULUM = _MICRO.parent
_REPO = _CURRICULUM.parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from literacy_pedagogy import frames_for_stage  # noqa: E402

_STAGE = "stage-04-meta-phonology-vowel-consonant"
_ORDER_FILE = _REPO / "lessons" / "literacy-cards" / "data" / "ru-phonology-ingest-order-v1.txt"


def _frames_in_order(manifest: dict, order_path: Path, *, all_remaining: bool) -> list[dict]:
    by_id = {
        str(f["id"]): f
        for f in frames_for_stage(manifest, _STAGE, limit=0, order="manifest")
    }
    ordered: list[dict] = []
    seen: set[str] = set()
    for ln in order_path.read_text(encoding="utf-8").splitlines():
        fid = ln.strip()
        if not fid or fid.startswith("#"):
            continue
        fr = by_id.get(fid)
        if fr is None:
            raise SystemExit(f"unknown frame in order file: {fid!r}")
        ordered.append(fr)
        seen.add(fid)
    if all_remaining:
        for fid in sorted(by_id):
            if fid not in seen:
                ordered.append(by_id[fid])
    return ordered


def _run(session, args: argparse.Namespace) -> None:
    manifest = session.load_manifest()
    order_path = args.order_file or _ORDER_FILE
    frames = _frames_in_order(manifest, order_path, all_remaining=args.all_frames)
    session.log({"stage": _STAGE, "frames": len(frames), "order": str(order_path.name)})
    for i, frame in enumerate(frames):
        fid = str(frame.get("id"))
        session.ingest(f"phon-{fid}"[:80], steps_for_frame(frame), i=i + 1, frame_id=fid)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--order-file", type=Path, default=None)
    p.add_argument(
        "--all-frames",
        action="store_true",
        help="after order file, ingest remaining stage frames (full 33 letters)",
    )
    args = p.parse_args()
    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file="summary-phonology-meta-stage.json",
        summary_builder=lambda s: {"stage": _STAGE, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
