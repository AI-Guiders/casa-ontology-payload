#!/usr/bin/env python3
"""Export beats JSON + Qwen prompt for a manifest chapter (round-trip refinement)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPT = REPO / "tools" / "qwen_listen_beats_prompt.txt"


def _export_beats_for_qwen(scene: dict) -> list[dict]:
    rows: list[dict] = []
    for beat in scene.get("beats") or []:
        if not isinstance(beat, dict):
            continue
        row: dict = {
            "id": beat.get("id"),
            "kind": beat.get("kind") or "paired",
            "t0": beat.get("t0"),
            "t1": beat.get("t1"),
            "note": beat.get("note") or "",
        }
        if row["kind"] == "motion" and isinstance(beat.get("keyframes"), list):
            row["keyframes"] = [
                {"frame_t": k.get("frame_t"), "note": k.get("note") or ""}
                for k in beat["keyframes"]
                if isinstance(k, dict) and "frame_t" in k
            ]
        elif beat.get("frame_t") is not None:
            row["frame_t"] = beat.get("frame_t")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export beats + Qwen prompt for refinement")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chapter", type=int, default=0)
    parser.add_argument("--out-beats", type=Path, default=None)
    parser.add_argument("--out-prompt", type=Path, default=None)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        if int(scene.get("chapter_index", -1)) != args.chapter:
            continue
        beats = _export_beats_for_qwen(scene)
        beats_path = args.out_beats or (manifest.parent / f"qwen-ch{args.chapter:02d}-beats.json")
        beats_path.write_text(json.dumps(beats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        prompt_text = PROMPT.read_text(encoding="utf-8").replace(
            "PASTE_BEATS_HERE",
            json.dumps(beats, ensure_ascii=False, indent=2),
        )
        prompt_path = args.out_prompt or (manifest.parent / f"qwen-ch{args.chapter:02d}-prompt.txt")
        prompt_path.write_text(prompt_text, encoding="utf-8")
        print(json.dumps({"beats": str(beats_path), "prompt": str(prompt_path), "count": len(beats)}, ensure_ascii=False))
        return 0

    print(f"chapter {args.chapter} not found", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
