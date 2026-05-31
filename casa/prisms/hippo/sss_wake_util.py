#!/usr/bin/env python3
"""Shared wake/surface scoring — top surface, normalize, auto-episode gate."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
import unicodedata
from typing import Any


def norm_text(text: str) -> str:
    t = unicodedata.normalize("NFC", (text or "").strip().lower())
    return re.sub(r"\s+", "", t)


def concept_to_surface(concept_id: str) -> str:
    cid = concept_id or ""
    for prefix in ("lang.word.", "syllable.", "grapheme."):
        if cid.startswith(prefix):
            return cid[len(prefix) :]
    return cid.split(".", 1)[-1]


def wake_surface_text(wake: dict) -> str:
    return str(wake.get("surface_text") or wake.get("babble_text") or "")


def top_surface(wake: dict) -> dict[str, Any] | None:
    active = wake.get("active") or []
    if not active:
        return None
    top = active[0]
    cid = str(top.get("concept_id") or "")
    return {
        "concept_id": cid,
        "surface": concept_to_surface(cid),
        "votes": int(top.get("votes") or 0),
    }


def parse_surfaces_from_text(wake: dict, *, limit: int = 4) -> list[str]:
    text = wake_surface_text(wake)
    m = re.search(r"Surface L\d:\s*(.+?)(?:\.|$)", text)
    if not m:
        m = re.search(r"Surface [^:]+:\s*(.+?)(?:\.|$)", text)
    if not m:
        m = re.search(r"Лепет L\d:\s*(.+?)(?:\.|$)", text)
    if not m:
        m = re.search(r"Лепет [^:]+:\s*(.+?)(?:\.|$)", text)
    if not m:
        return []
    body = m.group(1).strip()
    if body.startswith("«"):
        end = body.find("»")
        if end >= 0:
            return [body[1:end]]
        return [body.strip("«»")]
    parts = re.split(r"[,\\s]+", body.replace(",", " "))
    return [p for p in parts if p][:limit]


def surface_matches_target(wake: dict, target: str, *, lattice_id: str | None = None) -> bool:
    want = norm_text(target)
    if not want:
        return False
    top = top_surface(wake)
    if top and norm_text(str(top["surface"])) == want:
        return True
    for surf in parse_surfaces_from_text(wake):
        if norm_text(surf) == want:
            return True
    if lattice_id == "L0_grapheme" and want:
        joined = norm_text("".join(parse_surfaces_from_text(wake, limit=8)))
        if joined.startswith(want) or want in joined:
            return True
    return False


def cue_joined_for_lattice(cue: str, *, lattice_id: str) -> str:
    """Heard stream: spaced letters «в о л к» → «волк»; open syllable «п а» → «па»."""
    parts = [p.strip() for p in cue.split() if p.strip()]
    if len(parts) > 1 and lattice_id in ("L0_grapheme", "L1_syllable", "L2_word"):
        return norm_text("".join(parts))
    return norm_text(cue)


def rank_for_cue(
    ranked: list[tuple[str, int]],
    cue: str,
    *,
    lattice_id: str,
) -> list[tuple[str, int]]:
    """Boost concepts matching heard cue (minimal compose hint, no claims_nav)."""
    if not cue.strip() or not ranked:
        return ranked
    cue_joined = cue_joined_for_lattice(cue, lattice_id=lattice_id)
    cue_chars = set(cue_joined)
    spaced_parts = [p.strip() for p in cue.split() if p.strip()]
    max_v = max(v for _, v in ranked)
    exact_boost = max_v + 1

    def boost(cid: str) -> int:
        surf = norm_text(concept_to_surface(cid))
        if not surf:
            return 0
        if lattice_id == "L1_syllable" and surf == cue_joined:
            return exact_boost
        if lattice_id == "L2_word" and surf == cue_joined:
            return exact_boost
        if lattice_id == "L0_grapheme" and surf in cue_chars:
            return 500
        if (
            lattice_id == "L1_syllable"
            and len(cue_joined) == 2
            and len(spaced_parts) == 2
            and set(surf) <= cue_chars
            and len(surf) >= 2
        ):
            return 200
        return 0

    return sorted(ranked, key=lambda x: (-(x[1] + boost(x[0])), x[0]))


def cue_from_wake(wake: dict) -> str:
    text = wake_surface_text(wake)
    m = re.search(r"Слышал:\s*«([^»]+)»", text)
    return m.group(1).strip() if m else ""


def internal_target_from_cue(cue: str, *, lattice_id: str) -> str:
    return cue_joined_for_lattice(cue, lattice_id=lattice_id)


def needs_self_correction(
    wake: dict,
    cue: str,
    *,
    lattice_id: str,
    external_target: str | None = None,
) -> tuple[bool, str]:
    """Agent notices surface ≠ internal expectation; returns (needs_fix, internal_target)."""
    target = (external_target or "").strip() or internal_target_from_cue(cue, lattice_id=lattice_id)
    if not target:
        return False, target
    ok = surface_matches_target(wake, target, lattice_id=lattice_id)
    return not ok, target


def surface_attempt_from_wake(wake: dict, *, lattice_id: str | None = None) -> str:
    top = top_surface(wake)
    if top:
        return str(top["surface"])
    parsed = parse_surfaces_from_text(wake, limit=1)
    if parsed:
        return parsed[0]
    if lattice_id == "L0_grapheme":
        joined = "".join(parse_surfaces_from_text(wake, limit=8))
        return joined[:80]
    return cue_from_wake(wake)[:80]
