#!/usr/bin/env python3
"""Morph role meta cards (lang.meta.morph.*) + segment JPEG — block 9c."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import MORPH_ROLE_CARDS, MORPH_SEGMENT_CARDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LESSON_ID = "lesson-14-morphemics-meta"
STAGE_ID = "stage-14-morphemics-root-affix"
STAGE_TITLE = "Состав слова: роли морфем"
STAGE_ORDER = 140
FACE = "sans"


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 4:
        return 220
    if n <= 10:
        return 160
    if n <= 18:
        return 130
    return 100


def build_frames() -> list[dict]:
    frames: list[dict] = []
    for slug, surface, concept_id in MORPH_ROLE_CARDS + MORPH_SEGMENT_CARDS:
        fid = f"word-{slug}-{FACE}"
        tag_kind = "morph:role" if concept_id.startswith("lang.meta.morph") else "morph:segment"
        frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:{tag_kind}:{slug}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [
                    concept_id,
                    f"surface:{surface}",
                    f"slug:{slug}",
                    f"face:{FACE}",
                    tag_kind,
                ],
                "lesson_id": LESSON_ID,
            }
        )
    return frames


def merge_manifest(frames: list[dict]) -> None:
    manifest_path = ROOT / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not any(s.get("id") == STAGE_ID for s in manifest.get("stages") or []):
        manifest.setdefault("stages", []).append(
            {
                "id": STAGE_ID,
                "title": STAGE_TITLE,
                "order": STAGE_ORDER,
                "lesson_id": LESSON_ID,
            }
        )
    by_id = {str(f.get("id")): f for f in manifest.get("frames") or []}
    for frame in frames:
        by_id[frame["id"]] = frame
    manifest["frames"] = list(by_id.values())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_jpegs(frames: list[dict]) -> None:
    out_dir = ROOT / LESSON_ID / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        fid = frame["id"]
        surface = next(
            (t.split(":", 1)[1] for t in frame.get("curriculum_tags") or [] if str(t).startswith("surface:")),
            fid,
        )
        draw_text_centered(surface, out_dir / f"{fid}.jpg", size=_font_size(surface))


def main() -> None:
    frames = build_frames()
    render_jpegs(frames)
    merge_manifest(frames)
    print(json.dumps({"frames": len(frames), "lesson": LESSON_ID, "stage": STAGE_ID}, ensure_ascii=False))


if __name__ == "__main__":
    main()
