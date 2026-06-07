#!/usr/bin/env python3
"""Register meta cards (lang.meta.register.*) — JPEG + manifest merge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import REGISTER_META_CARDS, REGISTER_WORD_CARDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LESSON_ID = "lesson-07-meta-language"
STAGE_ID = "stage-07c-register-phrases"
STAGE_TITLE = "Категория: регистр слова и аббревиатуры"
STAGE_ORDER = 72
FACE = "sans"


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 6:
        return 200
    if n <= 14:
        return 150
    if n <= 28:
        return 120
    return 96


def build_frames() -> list[dict]:
    frames: list[dict] = []
    for slug, surface, concept_id in REGISTER_META_CARDS:
        fid = f"word-{slug}-{FACE}"
        frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:register:{slug}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [
                    concept_id,
                    f"surface:{surface}",
                    f"slug:{slug}",
                    f"face:{FACE}",
                    "grammar:register",
                ],
                "lesson_id": LESSON_ID,
            }
        )
    for slug, surface, concept_id in REGISTER_WORD_CARDS:
        fid = f"word-{slug}-{FACE}"
        frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:word:{slug}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [
                    concept_id,
                    f"word:{surface}",
                    f"surface:{surface}",
                    f"slug:{slug}",
                    f"face:{FACE}",
                    "register:allCaps",
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
                "lesson_ids": [LESSON_ID],
            }
        )
        manifest["stages"].sort(key=lambda s: int(s.get("order") or 0))
    ids = {str(f.get("id")) for f in manifest.get("frames") or []}
    for fr in frames:
        if fr["id"] not in ids:
            manifest.setdefault("frames", []).append(fr)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for slug, surface, _ in [*REGISTER_META_CARDS, *REGISTER_WORD_CARDS]:
        fid = f"word-{slug}-{FACE}"
        draw_text_centered(surface, img_dir / f"{fid}.jpg", size=_font_size(surface))
    frames = build_frames()
    merge_manifest(frames)
    print(json.dumps({"cards": len(frames), "stage": STAGE_ID}, ensure_ascii=False))


if __name__ == "__main__":
    main()
