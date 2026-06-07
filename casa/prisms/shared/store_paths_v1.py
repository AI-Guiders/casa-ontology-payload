#!/usr/bin/env python3
"""Prism layout v1: canonical store paths only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PRISM_LAYOUT_VERSION = 1

# Canonical subdirs under ltm/ (no legacy tier mirrors)
LTM_SUBDIRS: tuple[str, ...] = (
    "memory/grapheme",
    "memory/syllable",
    "memory/lexicon",
    "memory/phrase",
    "memory/math",
    "control",
    "hippo",
)


def manifest_layout_block() -> dict[str, Any]:
    return {"prism_layout_version": PRISM_LAYOUT_VERSION}


def ltm_tier_for_lattice(lattice_id: str) -> str:
    """Internal tier slug → canonical subdir key in LTM_SUBDIRS mapping."""
    lid = str(lattice_id)
    if lid.startswith("control-") or lid.startswith("lattice_"):
        return "control"
    if lid.startswith("lexicon-") or lid.startswith("words-"):
        return "memory/lexicon"
    if lid.startswith("alphabet-") or lid.startswith("punct-") or lid.startswith("layout-") or lid == "keys-physical":
        return "memory/grapheme"
    if lid.startswith("syllables-"):
        return "memory/syllable"
    if lid in ("phrases",):
        return "memory/phrase"
    if lid.startswith("phrases-"):
        return "memory/phrase"
    if lid.startswith(("schema-", "compose-", "cardinal-", "quantity-", "logic-", "math-axiom", "math-calculus")):
        return "memory/math"
    if lid in ("logic-laws", "math-axiom", "math-calculus-rules", "morph-role-ru"):
        return "memory/math" if lid != "morph-role-ru" else "memory/lexicon"
    if lid.startswith("episodic-"):
        return "hippo"
    if lid.startswith("L0_"):
        return "memory/grapheme"
    if lid.startswith("L1_"):
        return "memory/syllable"
    if lid.startswith("L2_"):
        return "memory/lexicon"
    if lid.startswith("L3_"):
        return "memory/phrase"
    if lid.startswith("H0_") or lid.startswith("F0_"):
        return "memory/math"
    return "memory/lexicon"


def canonical_ltm_subdir(lattice_id: str) -> Path:
    return Path(ltm_tier_for_lattice(lattice_id))


def ltm_ltm_filename(lattice_id: str) -> str:
    return f"{lattice_id}.ltm"


def ltm_write_targets(ltm_root: Path, lattice_id: str) -> tuple[Path, list[Path]]:
    """Primary canonical path only (no legacy mirrors)."""
    name = ltm_ltm_filename(lattice_id)
    primary = ltm_root / canonical_ltm_subdir(lattice_id) / name
    return primary, []


def ltm_scan_subdirs(ltm_dir: Path, *, manifest: dict[str, Any] | None = None) -> list[Path]:
    del manifest
    out: list[Path] = []
    seen: set[Path] = set()
    for rel in LTM_SUBDIRS:
        p = ltm_dir / rel
        if p.is_dir() and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def canonical_nca_relpath(lattice_id: str) -> Path:
    lid = str(lattice_id)
    if lid.startswith("control-"):
        return Path("control") / lid
    if lid.startswith("lexicon-") or lid.startswith("words-"):
        return Path("memory") / "lexicon" / lid
    if lid.startswith("alphabet-"):
        return Path("memory") / "grapheme" / lid
    if lid.startswith("syllables-"):
        return Path("memory") / "syllable" / lid
    if lid in ("phrases",):
        return Path("memory") / "phrase" / lid
    if lid.startswith("phrases-"):
        return Path("memory") / "phrase" / lid
    if lid.startswith(("schema-", "compose-", "cardinal-")):
        return Path("memory") / "math" / lid
    if lid.startswith("episodic-"):
        return Path("hippo") / lid
    return Path(lid)


def nca_dir_candidates(store_dir: Path, lattice_id: str) -> list[Path]:
    root = store_dir / "nca"
    canon = root / canonical_nca_relpath(lattice_id)
    return [canon]


def resolve_nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    for p in nca_dir_candidates(store_dir, lattice_id):
        if p.is_dir() and (p / "model.pt").is_file():
            return p
    return nca_dir_candidates(store_dir, lattice_id)[0]


def resolve_ltm_file(ltm_dir: Path, lattice_id: str, entry: dict[str, Any] | None = None) -> Path:
    """Find .ltm on disk: manifest path, then canonical subdir."""
    lid = str(lattice_id)
    if entry:
        p = entry.get("path")
        if p:
            cand = Path(p)
            if cand.is_file():
                return cand
            cand = ltm_dir.parent / p
            if cand.is_file():
                return cand
    primary, _aliases = ltm_write_targets(ltm_dir, lid)
    for cand in (primary,):
        for ext in ("", ".zst", ".gz"):
            path = Path(str(cand) + ext) if ext else cand
            if path.is_file():
                return path
            path2 = cand.with_suffix(cand.suffix + ext) if ext else cand
            if path2.is_file():
                return path2
    for sub in ltm_scan_subdirs(ltm_dir):
        for ext in ("", ".zst", ".gz"):
            base = sub / f"{lid}.ltm"
            cand = base if not ext else Path(str(base) + ext)
            if cand.is_file():
                return cand
    raise FileNotFoundError(f"no .ltm for {lid!r} under {ltm_dir}")
