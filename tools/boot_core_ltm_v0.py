#!/usr/bin/env python3
"""Merge immutable agent-core ltm packs (alphabet, VK layouts) into runtime field."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alphabet_core_v0 import merge_alphabet_l0_from_ltm  # type: ignore
from import_ltm_pack_v0 import import_pack  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from vk_layout_field_v0 import L0_VK_MAP_ID, compose_index_from_state  # type: ignore


def _repo_root(root: Path | None) -> Path:
    return root or Path(__file__).resolve().parent.parent


def default_alphabet_core_ltm_dir(*, root: Path | None = None) -> Path:
    return _repo_root(root) / "lab/agent-core/alphabet-v0/ltm"


def default_core_ltm_dir(*, root: Path | None = None) -> Path:
    return _repo_root(root) / "lab/agent-core/vk-layouts-v0/ltm"


def merge_core_ltm(
    state: dict,
    core_ltm_dir: Path,
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import VK layouts core (L0_vk_map + L0_grapheme overlay)."""
    state = ensure_prisms(state)
    core_ltm_dir = core_ltm_dir.resolve()
    manifest_path = core_ltm_dir / "pack.manifest.json"
    if manifest is None:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"core ltm manifest missing: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    imp = import_pack(state, core_ltm_dir, manifest=manifest)
    idx = compose_index_from_state(state)
    state.setdefault("store", {})["core_ltm_vk"] = str(core_ltm_dir)
    return {
        "import": imp,
        "lattice_id": L0_VK_MAP_ID,
        "mapping_count": len(idx or {}),
        "immutable": bool(manifest.get("immutable")),
        "kind": manifest.get("kind"),
    }


def merge_core_ltm_stack(
    state: dict,
    *,
    root: Path | None = None,
    include_alphabet: bool = True,
    include_vk: bool = True,
    alphabet_ltm: Path | None = None,
    vk_ltm: Path | None = None,
) -> dict[str, Any]:
    """Alphabet first (RU 33 + EN 26), then VK layouts merge on L0."""
    state = ensure_prisms(state)
    root = _repo_root(root)
    report: dict[str, Any] = {}
    if include_alphabet:
        altm = (alphabet_ltm or default_alphabet_core_ltm_dir(root=root)).resolve()
        if altm.joinpath("pack.manifest.json").is_file():
            report["alphabet"] = merge_alphabet_l0_from_ltm(state, altm)
        else:
            report["alphabet"] = {"skipped": "manifest missing", "path": str(altm)}
    if include_vk:
        vltm = (vk_ltm or default_core_ltm_dir(root=root)).resolve()
        if vltm.joinpath("pack.manifest.json").is_file():
            report["vk"] = merge_core_ltm(state, vltm)
        else:
            report["vk"] = {"skipped": "manifest missing", "path": str(vltm)}
    state.setdefault("store", {})["core_ltm_stack"] = report
    return report


def core_ltm_from_profile(profile: dict[str, Any], *, root: Path) -> Path | None:
    core = profile.get("core_ltm")
    if isinstance(core, str):
        p = Path(core)
        return p if p.is_absolute() else (root / p).resolve()
    if isinstance(core, dict):
        ltm = core.get("ltm_dir")
        if ltm:
            p = Path(str(ltm))
            return p if p.is_absolute() else (root / p).resolve()
    return None
