#!/usr/bin/env python3
"""Shared headword I/O and extraction from agent-store L2 lattices."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import is_l2_en_word_lattice, is_l2_word_lattice  # type: ignore
from sss_stack_v0 import decode_lattice  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore

_L2_WORD_RE = re.compile(r"^W:(.+)$")
_L2_CONCEPT_RE = re.compile(r"^lang\.word\.(.+)$")

RU_WORD_RE = re.compile(r"[а-яё]+(?:-[а-яё]+)?", re.IGNORECASE)
EN_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)


def read_headwords(path: Path | str) -> list[str]:
    p = Path(path)
    words: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        w = norm_word(line.split("#", 1)[0].strip())
        if w and not w.startswith("#"):
            words.append(w)
    return list(dict.fromkeys(words))


def write_headwords(path: Path, words: list[str], *, header: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if header:
        lines.append(f"# {header}")
    lines.extend(words)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_words_from_store(state: dict) -> dict[str, int]:
    """Headwords + vote weight from RU L2_word_* or EN L2_en_word_* lattices."""
    votes: dict[str, int] = {}
    for lid, lat in memory_lattices(state).items():
        if not (is_l2_word_lattice(lid) or is_l2_en_word_lattice(lid)):
            continue
        for cell in lat.get("cells") or []:
            for t in cell:
                m = _L2_WORD_RE.match(str(t))
                if m:
                    w = norm_word(m.group(1))
                    if w:
                        votes[w] = votes.get(w, 0) + 1
        dec = decode_lattice(lat, min_votes=1)
        for c in dec.get("concepts") or []:
            cid = str(c.get("concept_id") or "")
            m = _L2_CONCEPT_RE.match(cid)
            if m:
                w = norm_word(m.group(1))
                if w:
                    votes[w] = max(votes.get(w, 0), int(c.get("votes") or 1))
    return votes


def export_headwords_from_store(store_dir: Path, out: Path, *, min_votes: int = 1) -> dict[str, Any]:
    fs = store_dir / "field_state.json"
    if not fs.is_file():
        raise FileNotFoundError(f"field_state missing: {fs}")
    state = ensure_prisms(load_field_state(fs))
    votes = collect_words_from_store(state)
    words = sorted(w for w, v in votes.items() if v >= min_votes)
    write_headwords(out, words, header=f"extracted from {store_dir.name}")
    return {
        "store_dir": str(store_dir.resolve()),
        "out": str(out.resolve()),
        "unique_headwords": len(words),
        "min_votes": min_votes,
    }


def tokenize_text(text: str, *, locale: str) -> list[str]:
    text = text.lower()
    if locale.startswith("ru"):
        return [norm_word(m.group(0)) for m in RU_WORD_RE.finditer(text)]
    return [norm_word(m.group(0)) for m in EN_WORD_RE.finditer(text)]
