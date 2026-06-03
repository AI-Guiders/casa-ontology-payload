#!/usr/bin/env python3
"""RU syllable cards (whole syllable on frame) → syllables-ru."""

from __future__ import annotations

import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literacy_render import draw_text_centered  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACE = "sans"

# Частотные слоги (целый знак на кадре)
SYLLABLES_RU: list[str] = [
    "ма", "па", "на", "та", "са", "ра", "ла", "ка", "ва", "да",
    "мо", "по", "но", "то", "со", "ро", "ло", "ко", "во", "до",
    "му", "пу", "ну", "ту", "су", "ру", "лу", "ку", "ву", "ду",
    "мы", "вы", "ни", "ти", "си", "ри", "ли", "ки", "ви", "ди",
    "при", "про", "пре", "раз", "без", "над", "под", "от", "из", "об",
    "ста", "ско", "ство", "ние", "ение", "ость",
]


def syllable_slug(s: str) -> str:
    return s.replace("ё", "yo")


def main() -> None:
    lesson = "lesson-05-syllables-cyrl"
    img_dir = ROOT / lesson / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict] = []
    for syl in SYLLABLES_RU:
        slug = syllable_slug(syl)
        fid = f"syllable-{slug}-{FACE}"
        draw_text_centered(syl, img_dir / f"{fid}.jpg", size=220)
        cid = f"syllable.{syl}"
        frames.append(
            {
                "id": fid,
                "path": f"{lesson}/images/{fid}.jpg",
                "scene_label": f"card:syllable:{slug}:{FACE}",
                "concept_id": cid,
                "curriculum_tags": [cid, f"face:{FACE}"],
                "lesson_id": lesson,
            }
        )

    manifest_path = ROOT / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("stages", [])
    if not any(s.get("id") == "stage-05-syllable-cyrl" for s in manifest["stages"]):
        manifest["stages"].append(
            {
                "id": "stage-05-syllable-cyrl",
                "title": "Слоги: кириллица (целые)",
                "order": 5,
                "lesson_ids": [lesson],
            }
        )
        manifest["stages"].sort(key=lambda s: int(s.get("order") or 0))
    ids = {f["id"] for f in manifest.get("frames") or []}
    for fr in frames:
        if fr["id"] not in ids:
            manifest.setdefault("frames", []).append(fr)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"syllables": len(frames)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
