#!/usr/bin/env python3
"""SRT subtitles → listen_mass manifest (sensory windows; no word cards by default)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _parse_time(ts: str) -> float:
    h, m, rest = ts.strip().replace(",", ".").split(":")
    s, ms = rest.split(".") if "." in rest else (rest, "0")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms[:3].ljust(3, "0")) / 1000.0


def parse_srt(
    content: str,
    *,
    source: str = "srt",
    include_words: bool = False,
) -> list[dict]:
    blocks = re.split(r"\n\s*\n", content.strip(), flags=re.MULTILINE)
    scenes: list[dict] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if "-->" in lines[1] else lines[0]
        text_lines = lines[2:] if "-->" in lines[1] else lines[1:]
        if "-->" not in time_line:
            continue
        left, right = [x.strip() for x in time_line.split("-->", 1)]
        t0 = _parse_time(left)
        t1 = _parse_time(right)
        caption = " ".join(text_lines).strip()
        idx = len(scenes) + 1
        row: dict = {
            "id": f"{source}-{idx:05d}",
            "source": source,
            "t0": round(t0, 3),
            "t1": round(t1, 3),
            "lang": "ru",
        }
        if caption:
            row["caption"] = caption
        if include_words and caption:
            row["words"] = list(dict.fromkeys(re.findall(r"[\w\-]+", caption.lower(), flags=re.UNICODE)))
            row["punctuation"] = [ch for ch in caption if ch in ".,!?;:"]
        scenes.append(row)
    return scenes


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert .srt to listen_mass manifest.ndjson")
    parser.add_argument("srt", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--source", default=None, help="source id prefix (default: srt stem)")
    parser.add_argument(
        "--with-words",
        action="store_true",
        help="Include explicit words[] (reading lesson path only)",
    )
    args = parser.parse_args()
    source = args.source or args.srt.stem
    content = args.srt.read_text(encoding="utf-8", errors="replace")
    scenes = parse_srt(content, source=source, include_words=args.with_words)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for scene in scenes:
            fh.write(json.dumps(scene, ensure_ascii=False) + "\n")
    print(f"wrote {len(scenes)} scenes → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
