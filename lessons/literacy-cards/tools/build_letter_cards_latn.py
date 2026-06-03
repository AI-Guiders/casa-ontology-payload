#!/usr/bin/env python3
"""EN a-z lower/upper cards → grapheme.latn.*"""

from __future__ import annotations

import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literacy_render import draw_text_centered  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACE = "sans"
LETTERS = "abcdefghijklmnopqrstuvwxyz"


def grapheme_cid(ch: str, register: str) -> str:
    return f"grapheme.latn.{ch}.{register}"


def frame_id(ch: str, register: str) -> str:
    return f"letter-{ch}-{register}-{FACE}"


def main() -> None:
    lesson = "lesson-11-letters-latn"
    img_dir = ROOT / lesson / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict] = []
    for ch in LETTERS:
        for register, glyph in (("lower", ch), ("upper", ch.upper())):
            fid = frame_id(ch, register)
            draw_text_centered(glyph, img_dir / f"{fid}.jpg", size=280)
            cid = grapheme_cid(ch, register)
            frames.append(
                {
                    "id": fid,
                    "path": f"{lesson}/images/{fid}.jpg",
                    "scene_label": f"card:letter:{ch}:{register}:{FACE}",
                    "concept_id": cid,
                    "curriculum_tags": [cid, f"register:{register}", f"cue:{ch}", f"face:{FACE}"],
                    "lesson_id": lesson,
                }
            )

    manifest_path = ROOT / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not any(s.get("id") == "stage-11-grapheme-latn" for s in manifest.get("stages") or []):
        manifest.setdefault("stages", []).append(
            {
                "id": "stage-11-grapheme-latn",
                "title": "Letters: Latin a-z",
                "order": 11,
                "lesson_ids": [lesson],
            }
        )
        manifest["stages"].sort(key=lambda s: int(s.get("order") or 0))
    ids = {f["id"] for f in manifest.get("frames") or []}
    for fr in frames:
        if fr["id"] not in ids:
            manifest.setdefault("frames", []).append(fr)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"letters": len(frames)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
