#!/usr/bin/env python3
"""Parse WebVTT/auto-caption → text window for listen scene caption (L3, not L2 oracle)."""

from __future__ import annotations

import re
from pathlib import Path

_TIME_ARROW = re.compile(
    r"^(?P<t0>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*(?P<t1>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})",
)


def _clock_to_sec(ts: str) -> float:
    raw = ts.strip().replace(",", ".")
    parts = raw.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(raw)


def load_vtt_cues(path: Path | str) -> list[dict[str, float | str]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    cues: list[dict[str, float | str]] = []
    idx = 0
    while idx < len(text):
        line_end = text.find("\n", idx)
        if line_end < 0:
            line_end = len(text)
        line = text[idx:line_end].strip()
        idx = line_end + 1
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.isdigit():
            continue
        m = _TIME_ARROW.match(line)
        if not m:
            continue
        t0 = _clock_to_sec(m.group("t0"))
        t1 = _clock_to_sec(m.group("t1"))
        body: list[str] = []
        while idx < len(text):
            line_end = text.find("\n", idx)
            if line_end < 0:
                line_end = len(text)
            row = text[idx:line_end].strip()
            idx = line_end + 1
            if not row:
                break
            if _TIME_ARROW.match(row):
                idx -= len(row) + 1
                break
            body.append(row)
        cap = " ".join(body).strip()
        if cap:
            cues.append({"t0": t0, "t1": t1, "text": cap})
    return cues


def find_vtt_file(bundle_dir: Path) -> Path | None:
    for path in sorted(bundle_dir.glob("*.vtt")):
        if path.is_file():
            return path
    for path in sorted(bundle_dir.glob("*.ru.vtt")):
        if path.is_file():
            return path
    return None


def caption_for_window(
    cues: list[dict[str, float | str]],
    *,
    t0: float,
    t1: float,
    fallback: str = "",
    max_chars: int = 1200,
) -> str:
    parts: list[str] = []
    for cue in cues:
        c0 = float(cue["t0"])
        c1 = float(cue["t1"])
        if c1 <= t0 or c0 >= t1:
            continue
        txt = str(cue.get("text") or "").strip()
        if txt and txt not in parts:
            parts.append(txt)
    out = " ".join(parts).strip()
    if not out:
        out = str(fallback or "").strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out
