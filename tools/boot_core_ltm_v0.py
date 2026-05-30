#!/usr/bin/env python3
"""Merge immutable core ltm (VK layouts) into runtime field state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from import_ltm_pack_v0 import import_pack  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore
from vk_layout_field_v0 import L0_VK_MAP_ID, compose_index_from_state  # type: ignore


def default_core_ltm_dir(*, root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent.parent
    return base / "examples/agent-core/vk-layouts-v0/ltm"


def merge_core_ltm(
    state: dict,
    core_ltm_dir: Path,
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    core_ltm_dir = core_ltm_dir.resolve()
    manifest_path = core_ltm_dir / "pack.manifest.json"
    if manifest is None:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"core ltm manifest missing: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    imp = import_pack(state, core_ltm_dir, manifest=manifest)
    idx = compose_index_from_state(state)
    state.setdefault("store", {})["core_ltm"] = str(core_ltm_dir)
    return {
        "import": imp,
        "lattice_id": L0_VK_MAP_ID,
        "mapping_count": len(idx or {}),
        "immutable": bool(manifest.get("immutable")),
    }


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
