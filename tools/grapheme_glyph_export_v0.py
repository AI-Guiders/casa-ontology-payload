#!/usr/bin/env python3
"""Export cursive grapheme PNGs from a TTF (Script MT / Propisi) for L0 visuals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

from fontTools.ttLib import TTFont  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore

from grapheme_ingest_v0 import (  # type: ignore
    concept_id_for_grapheme,
    derive_graphemes_from_words,
)
from sss_vocab_v0 import norm_word  # type: ignore

Script = Literal["latn", "cyrl"]
STYLE_CURSIVE = "cursive"

LATN_ALPHABET = [chr(c) for c in range(ord("a"), ord("z") + 1)]
CYRL_ALPHABET = list("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")

DEFAULT_WIN_LATN = Path(r"C:\Windows\Fonts\SCRIPTBL.TTF")
DEFAULT_WIN_LATN_ALT = Path(r"C:\Windows\Fonts\FRSCRIPT.TTF")


def _font_cmap(font_path: Path) -> dict[int, str]:
    tt = TTFont(str(font_path))
    return dict(tt.getBestCmap() or {})


def _font_has_char(font_path: Path, ch: str) -> bool:
    return ord(ch) in _font_cmap(font_path)


def _resolve_latn_font(explicit: Path | None, repo_fonts: Path) -> Path | None:
    if explicit and explicit.is_file():
        return explicit
    for cand in (
        repo_fonts / "ScriptS.ttf",
        repo_fonts / "ofont.ru_ScriptS.ttf",
        repo_fonts / "ScriptMTBold.ttf",
        repo_fonts / "SCRIPTBL.TTF",
        DEFAULT_WIN_LATN,
        DEFAULT_WIN_LATN_ALT,
    ):
        if cand.is_file():
            return cand
    return None


def _resolve_cyrl_font(explicit: Path | None, repo_fonts: Path) -> Path | None:
    if explicit and explicit.is_file():
        return explicit
    for cand in (
        repo_fonts / "ScriptS.ttf",
        repo_fonts / "ofont.ru_ScriptS.ttf",
        repo_fonts / "Propisi.ttf",
        repo_fonts / "propisi.ttf",
        repo_fonts / "PROPISI.TTF",
    ):
        if cand.is_file():
            return cand
    return None


def _render_glyph(
    font: ImageFont.FreeTypeFont,
    ch: str,
    *,
    canvas: int = 192,
    padding: int = 8,
) -> Image.Image:
    img = Image.new("RGBA", (canvas, canvas), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.text((padding, padding), ch, font=font, fill=(0, 0, 0, 255))
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(canvas, x1 + padding)
    y1 = min(canvas, y1 + padding)
    return img.crop((x0, y0, x1, y1))


def export_script_glyphs(
    *,
    font_path: Path,
    chars: list[str],
    script: Script,
    out_dir: Path,
    font_size: int = 96,
    style: str = STYLE_CURSIVE,
) -> dict[str, Any]:
    (out_dir / script).mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(font_path), font_size)
    family, weight = font.getname()
    entries: list[dict[str, Any]] = []
    missing: list[str] = []

    for ch in chars:
        key = ch.lower() if script == "latn" else ch
        render_ch = key if script == "latn" else ch
        if not _font_has_char(font_path, render_ch):
            missing.append(ch)
            continue
        png = _render_glyph(font, render_ch)
        cid = concept_id_for_grapheme(key, script)
        fname = f"{script}_{key}.png"
        rel = f"{script}/{fname}"
        png.save(out_dir / script / fname)
        entries.append(
            {
                "concept_id": cid,
                "char": key,
                "script": script,
                "style": style,
                "png": rel.replace("\\", "/"),
                "font_file": font_path.name,
                "font_family": family,
                "font_weight": weight,
            }
        )

    return {
        "script": script,
        "font_path": str(font_path),
        "font_family": family,
        "exported": len(entries),
        "missing": missing,
        "entries": entries,
    }


def write_manifest(out_root: Path, reports: list[dict[str, Any]], *, schema_version: int = 1) -> Path:
    all_entries: list[dict[str, Any]] = []
    for rep in reports:
        all_entries.extend(rep.get("entries") or [])
    doc = {
        "schema_version": schema_version,
        "style": STYLE_CURSIVE,
        "glyph_count": len(all_entries),
        "sources": [
            {
                "script": r.get("script"),
                "font_path": r.get("font_path"),
                "font_family": r.get("font_family"),
                "exported": r.get("exported"),
                "missing": r.get("missing"),
            }
            for r in reports
        ],
        "glyphs": all_entries,
    }
    path = out_root / "manifest.v1.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Export cursive grapheme PNGs from TTF")
    p.add_argument(
        "--out",
        type=Path,
        default=root / "lab/exp_bilingual_v0/grapheme-glyphs",
    )
    p.add_argument(
        "--fonts-dir",
        type=Path,
        default=root / "lab/exp_bilingual_v0/fonts",
    )
    p.add_argument("--latn-font", type=Path, default=None, help="Default: Script MT Bold on Windows")
    p.add_argument("--cyrl-font", type=Path, default=None, help="Default: Propisi.ttf in fonts-dir")
    p.add_argument("--font-size", type=int, default=96)
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--latn-only", action="store_true")
    args = p.parse_args()

    out_root = args.out.resolve()
    fonts_dir = args.fonts_dir.resolve()

    latn_font = _resolve_latn_font(args.latn_font, fonts_dir)
    if not latn_font:
        print("ERROR: no Latin cursive font (Script MT Bold / --latn-font)", file=sys.stderr)
        raise SystemExit(1)

    headwords = [
        norm_word(line)
        for line in args.headwords.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    latn_chars = derive_graphemes_from_words(headwords, "latn") or LATN_ALPHABET

    reports: list[dict[str, Any]] = []
    latn_rep = export_script_glyphs(
        font_path=latn_font,
        chars=latn_chars,
        script="latn",
        out_dir=out_root,
        font_size=args.font_size,
    )
    reports.append(latn_rep)
    print(f"latn: {latn_rep['exported']} glyphs from {latn_font.name} ({latn_rep['font_family']})")

    if not args.latn_only:
        cyrl_font = _resolve_cyrl_font(args.cyrl_font, fonts_dir)
        if cyrl_font:
            cyrl_rep = export_script_glyphs(
                font_path=cyrl_font,
                chars=CYRL_ALPHABET,
                script="cyrl",
                out_dir=out_root,
                font_size=args.font_size,
            )
            reports.append(cyrl_rep)
            print(f"cyrl: {cyrl_rep['exported']} glyphs from {cyrl_font.name} ({cyrl_rep['font_family']})")
        else:
            print(
                "cyrl: skipped — place Propisi.ttf in lab/exp_bilingual_v0/fonts/ "
                "(Script MT has no Cyrillic)",
                file=sys.stderr,
            )

    manifest = write_manifest(out_root, reports)
    print(json.dumps({"manifest": str(manifest), "glyph_count": sum(r["exported"] for r in reports)}, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
