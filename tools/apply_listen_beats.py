#!/usr/bin/env python3
"""Merge external beat JSON (e.g. Qwen) into manifest + extract frames."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.domain.listen_beat_apply import apply_external_beats_to_scene, load_external_beats
from casa.domain.listen_beat_verify import format_beat_report, validate_scene_beats


def _find_video(bundle_dir: Path) -> Path:
    for ext in ("webm", "mp4", "mkv"):
        candidate = bundle_dir / f"video.{ext}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no video.* in {bundle_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply external listen beats to manifest chapter(s)")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--beats", type=Path, required=True, help="JSON array [{id,t0,t1,frame_t,note?}, ...]")
    parser.add_argument("--chapters", type=str, default="0", help="comma chapter indices")
    parser.add_argument("--beat-source", type=str, default="qwen")
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    bundle_dir = manifest.parent
    video_path = _find_video(bundle_dir)
    external = load_external_beats(args.beats.resolve())
    want = {int(x.strip()) for x in args.chapters.split(",") if x.strip()}

    scenes: list[dict] = []
    applied = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        idx = scene.get("chapter_index")
        if idx is not None and int(idx) in want:
            scene = apply_external_beats_to_scene(
                scene,
                external,
                bundle_dir=bundle_dir,
                video_path=video_path,
                beat_source=args.beat_source,
            )
            applied += 1
        scenes.append(scene)

    if applied == 0:
        print("no chapters matched", file=sys.stderr)
        return 2

    with manifest.open("w", encoding="utf-8") as fh:
        for scene in scenes:
            fh.write(json.dumps(scene, ensure_ascii=False) + "\n")

    print(json.dumps({"manifest": str(manifest), "chapters_applied": applied, "beats": len(external)}, ensure_ascii=False))

    for scene in scenes:
        idx = scene.get("chapter_index")
        if idx is not None and int(idx) in want:
            check = validate_scene_beats(scene, bundle_dir)
            title = str(scene.get("chapter_title") or scene.get("caption") or "")
            print()
            print(format_beat_report(check, scene_title=title))
            return 0 if check.ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
