#!/usr/bin/env python3
"""Prism layout v1: canonical store paths + legacy aliases (M1)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

PRISM_LAYOUT_VERSION = 1

# legacy ltm/<tier> → canonical path under ltm/
LTM_TIER_ALIASES: dict[str, str] = {
    "l0": "memory/grapheme",
    "l1": "memory/syllable",
    "l2": "memory/lexicon",
    "l3": "memory/phrase",
    "h0": "memory/math",
    "lat": "memory/lexicon",
    "ctrl": "control",
}


def manifest_layout_block() -> dict[str, Any]:
    return {
        "prism_layout_version": PRISM_LAYOUT_VERSION,
        "path_aliases": {f"ltm/{k}": f"ltm/{v}" for k, v in LTM_TIER_ALIASES.items()},
    }


def merge_path_aliases(manifest: dict[str, Any] | None) -> dict[str, str]:
    out = dict(LTM_TIER_ALIASES)
    if manifest:
        raw = manifest.get("path_aliases") or {}
        for k, v in raw.items():
            key = str(k).removeprefix("ltm/")
            val = str(v).removeprefix("ltm/")
            out[key] = val
    return out


def legacy_ltm_tier(lattice_id: str) -> str:
    """Legacy single-segment dir under ltm/ (l0, l2, lat, ctrl, …)."""
    lid = str(lattice_id)
    if lid.startswith("control-") or lid.startswith("lattice_"):
        return "ctrl"
    if lid.startswith("lexicon-") or lid.startswith("words-"):
        return "l2"
    if lid.startswith("alphabet-") or lid.startswith("punct-") or lid.startswith("layout-") or lid == "keys-physical":
        return "l0"
    if lid.startswith("syllables-"):
        return "l1"
    if lid in ("phrases",):
        return "l3"
    if lid.startswith(("schema-", "compose-", "cardinal-", "quantity-")):
        return "h0"
    if lid.startswith("L0_"):
        return "l0"
    if lid.startswith("L1_"):
        return "l1"
    if lid.startswith("L2_"):
        return "l2"
    if lid.startswith("L3_"):
        return "l3"
    if lid.startswith("H0_"):
        return "h0"
    return "lat"


def canonical_ltm_subdir(lattice_id: str) -> Path:
    """Path relative to ltm/, e.g. memory/lexicon."""
    tier = legacy_ltm_tier(lattice_id)
    mapped = LTM_TIER_ALIASES.get(tier, tier)
    return Path(mapped)


def ltm_ltm_filename(lattice_id: str) -> str:
    return f"{lattice_id}.ltm"


def ltm_write_targets(ltm_root: Path, lattice_id: str) -> tuple[Path, list[Path]]:
    """Primary (canonical) file and legacy alias paths to mirror."""
    name = ltm_ltm_filename(lattice_id)
    primary = ltm_root / canonical_ltm_subdir(lattice_id) / name
    aliases: list[Path] = []
    tier = legacy_ltm_tier(lattice_id)
    legacy = ltm_root / tier / name
    if legacy != primary:
        aliases.append(legacy)
    if tier == "l2":
        lat = ltm_root / "lat" / name
        if lat not in (primary, *aliases):
            aliases.append(lat)
    return primary, aliases


def mirror_ltm_file(primary: Path, alias: Path) -> None:
    alias.parent.mkdir(parents=True, exist_ok=True)
    if alias.is_file():
        alias.unlink()
    try:
        os.link(primary, alias)
    except OSError:
        shutil.copy2(primary, alias)


def ltm_scan_subdirs(ltm_dir: Path, *, manifest: dict[str, Any] | None = None) -> list[Path]:
    """Directories to scan for *.ltm (canonical + legacy tiers)."""
    aliases = merge_path_aliases(manifest)
    rels: set[str] = set(LTM_TIER_ALIASES) | set(aliases.values()) | set(aliases.keys())
    out: list[Path] = []
    seen: set[Path] = set()
    for rel in sorted(rels):
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
    if lid.startswith(("schema-", "compose-", "cardinal-")):
        return Path("memory") / "math" / lid
    if lid.startswith("episodic-"):
        return Path("hippo") / lid
    return Path(lid)


def nca_dir_candidates(store_dir: Path, lattice_id: str) -> list[Path]:
    root = store_dir / "nca"
    lid = str(lattice_id)
    canon = root / canonical_nca_relpath(lattice_id)
    flat = root / lid.replace("/", "_")
    out: list[Path] = []
    for p in (canon, flat):
        if p not in out:
            out.append(p)
    return out


def resolve_nca_lattice_dir(store_dir: Path, lattice_id: str) -> Path:
    for p in nca_dir_candidates(store_dir, lattice_id):
        if p.is_dir() and (p / "model.pt").is_file():
            return p
    return nca_dir_candidates(store_dir, lattice_id)[0]


def resolve_ltm_file(ltm_dir: Path, lattice_id: str, entry: dict[str, Any] | None = None) -> Path:
    """Find .ltm on disk: manifest path, then canonical, then legacy tiers."""
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
    primary, aliases = ltm_write_targets(ltm_dir, lid)
    for cand in (primary, *aliases):
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
