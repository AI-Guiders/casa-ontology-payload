#!/usr/bin/env python3
"""Положить literacy moment'ы в lab/inbox для agent_inbox_runner (один JSON = один sleep)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import steps_for_frame
from runner_infra import LITERACY, bootstrap, class_dir_for

bootstrap(__file__)
_REPO = Path(__file__).resolve().parents[3]
_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))
from literacy_pedagogy import default_wordlist_for_stage, frames_for_stage  # noqa: E402

_DEFAULT_OUT = _REPO / "lab" / "inbox"


def _inbox_payload(*, moment_id: str, steps: list[dict]) -> dict:
    return {
        "kind": "lesson_moment",
        "class_dir": "lessons/literacy-cards",
        "moment_id": moment_id,
        "steps": steps,
        "sleep": True,
    }


def enqueue_literacy_inbox(
    *,
    stage_id: str,
    out_dir: Path,
    limit: int = 0,
    offset: int = 0,
    prefix: str = "literacy",
    dry_run: bool = False,
    order: str = "wordlist",
    wordlist_path: Path | None = None,
) -> list[Path]:
    manifest_path = class_dir_for(LITERACY) / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wl = wordlist_path
    if wl is None and order == "wordlist":
        wl = default_wordlist_for_stage(stage_id)
    frames = frames_for_stage(
        manifest,
        stage_id,
        limit=limit,
        offset=offset,
        order=order,  # type: ignore[arg-type]
        wordlist_path=wl,
    )
    if not frames:
        raise SystemExit(f"no frames for stage {stage_id!r}")

    out_dir = out_dir.resolve()
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    width = max(3, len(str(len(frames))))
    for i, frame in enumerate(frames, start=1):
        fid = str(frame.get("id"))
        moment_id = f"lex-{stage_id}-{fid}"[:80]
        steps = steps_for_frame(frame)
        payload = _inbox_payload(moment_id=moment_id, steps=steps)
        name = f"{prefix}-{i:0{width}d}-{fid}.json"
        path = out_dir / name
        if dry_run:
            print(json.dumps({"would_write": str(path), "moment_id": moment_id}, ensure_ascii=False))
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    summary = {
        "stage": stage_id,
        "count": len(written),
        "out_dir": str(out_dir),
        "dry_run": dry_run,
        "reactor": "python tools/agent_inbox_runner.py --store-dir agents/von-neumann --inbox-dir lab/inbox",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return written


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", default="stage-06-words-cyrl-corpus")
    p.add_argument("--limit", type=int, default=20, help="max frames (0=all)")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--prefix", default="literacy")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--order",
        choices=("wordlist", "frame_id", "manifest"),
        default="wordlist",
    )
    p.add_argument("--wordlist", type=Path, default=None)
    args = p.parse_args()
    enqueue_literacy_inbox(
        stage_id=args.stage,
        out_dir=args.out_dir,
        limit=args.limit,
        offset=args.offset,
        prefix=args.prefix,
        dry_run=args.dry_run,
        order=args.order,
        wordlist_path=args.wordlist,
    )


if __name__ == "__main__":
    main()
