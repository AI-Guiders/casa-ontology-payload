#!/usr/bin/env python3
"""Tokenize running text — words + punctuation as seen in the stream."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
import unicodedata
from typing import Any, Literal

TokenKind = Literal["word", "punct"]

# Cyrillic words; punctuation runs (incl. hyphen between syllables, guillemets, ellipsis).
_STREAM_RE = re.compile(
    r"[а-яё]+|[\.!,;:?…—\-«»\"()]+",
    re.IGNORECASE | re.UNICODE,
)
_WORD_RE = re.compile(r"[а-яё]+", re.IGNORECASE | re.UNICODE)
_PUNCT_RE = re.compile(r"[\.!,;:?…—\-«»\"()]+", re.UNICODE)


def norm_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _is_word(surface: str) -> bool:
    return bool(_WORD_RE.fullmatch(surface))


_PUNCT_CHARS = set(".!,;:?—-«»\"()…")
_ELLIPSIS = "..."


def _split_punct_run(run: str) -> list[str]:
    """One stream token per visible mark (… and ... kept as units)."""
    out: list[str] = []
    i = 0
    while i < len(run):
        if run.startswith(_ELLIPSIS, i):
            out.append(_ELLIPSIS)
            i += 3
            continue
        ch = run[i]
        if ch in _PUNCT_CHARS:
            out.append(ch)
        i += 1
    return out


def extract_stream(text: str, *, min_word_len: int = 1) -> list[dict[str, Any]]:
    """Tokens in reading order: words (lower) + punctuation (single marks)."""
    t = norm_text(text).lower()
    out: list[dict[str, Any]] = []
    for m in _STREAM_RE.finditer(t):
        s = m.group(0)
        if not s:
            continue
        if _is_word(s):
            if len(s) >= min_word_len:
                out.append({"kind": "word", "surface": s})
        elif _PUNCT_RE.fullmatch(s):
            for mark in _split_punct_run(s):
                out.append({"kind": "punct", "surface": mark})
    return out


def extract_words(text: str, *, min_len: int = 1) -> list[str]:
    """Unique words in first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for tok in extract_stream(text, min_word_len=min_len):
        if tok["kind"] != "word":
            continue
        w = str(tok["surface"])
        if w not in seen:
            seen.add(w)
        out.append(w)
    return out


def extract_words_ordered(text: str, *, min_len: int = 1) -> list[str]:
    return [str(t["surface"]) for t in extract_stream(text, min_word_len=min_len) if t["kind"] == "word"]


def extract_punctuation_ordered(text: str) -> list[str]:
    return [str(t["surface"]) for t in extract_stream(text) if t["kind"] == "punct"]


def extract_punctuation_unique(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in extract_punctuation_ordered(text):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def split_paragraphs(text: str) -> list[str]:
    t = norm_text(text).strip()
    if not t:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    if parts:
        return parts
    return [ln.strip() for ln in t.splitlines() if ln.strip()] or [t]


def paragraphs_to_scenes(text: str, *, prefix: str = "p") -> list[dict]:
    scenes: list[dict] = []
    for i, para in enumerate(split_paragraphs(text)):
        stream = extract_stream(para)
        words = [t["surface"] for t in stream if t["kind"] == "word"]
        punct = [t["surface"] for t in stream if t["kind"] == "punct"]
        scenes.append(
            {
                "id": f"{prefix}{i + 1}",
                "caption": para[:240],
                "words": list(dict.fromkeys(words)),
                "punctuation": list(dict.fromkeys(punct)),
                "tokens": len(stream),
            }
        )
    return scenes
