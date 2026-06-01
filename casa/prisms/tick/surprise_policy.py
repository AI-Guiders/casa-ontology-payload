#!/usr/bin/env python3
"""Surprise episode / journal policy — dedup, casefold cues, avoid repeat «крик»."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from casa.prisms.memory.agent_journal import read_journal_entries
from casa.domain.prism_wire import prism_hippo


def normalize_cue(cue: str) -> str:
    """Case- and whitespace-insensitive cue key (orthographic variants → one)."""
    text = unicodedata.normalize("NFC", (cue or "").strip())
    return " ".join(text.casefold().split())


def surprise_signature(surprise: Iterable[str]) -> str:
    return "|".join(sorted(str(s) for s in surprise if s))


def find_predict_mismatch_episode(state: dict, *, norm_cue: str) -> dict | None:
    for ep in prism_hippo(state).get("episodes") or []:
        if ep.get("consolidated"):
            continue
        if ep.get("structure_tag") != "predict_mismatch":
            continue
        if normalize_cue(str(ep.get("cue") or "")) == norm_cue:
            return ep
    return None


def bump_episode_recurrence(ep: dict) -> dict:
    seen = int(ep.get("recurrence_seen") or 0) + 1
    return {**ep, "recurrence_seen": seen, "deduped": True}


def recent_journal_surprise_signatures(
    store_dir: Path,
    *,
    scope: str = "self",
    limit: int = 32,
) -> set[str]:
    sigs: set[str] = set()
    for row in read_journal_entries(store_dir, domain=scope, limit=limit):
        meta = row.get("meta") or {}
        data = meta.get("data") if isinstance(meta.get("data"), dict) else {}
        sig = data.get("surprise_signature")
        if sig:
            sigs.add(str(sig))
    return sigs


def should_skip_journal_surprise(
    store_dir: Path,
    *,
    sig: str,
    scope: str = "self",
) -> bool:
    return sig in recent_journal_surprise_signatures(store_dir, scope=scope)
