#!/usr/bin/env python3
"""Immutable keyboard core: physical + per-layout + punct lattices with lang/alphabet links."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grapheme_ingest_v0 import L0_CYRL_ID, L0_LATN_ID  # type: ignore
from ltm_pack_v0 import lattice_subdir, write_ltm  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from vk_layout_field_v0 import (  # type: ignore
    L0_LAYOUT_JCUKEN_ID,
    L0_LAYOUT_QWERTY_ID,
    L0_PUNCT_CYRL_ID,
    L0_PUNCT_LATN_ID,
    L0_VK_PHYSICAL_ID,
    KEYBOARD_CORE_KIND,
    VK_CORE_LATTICE_IDS,
    imprint_split_keyboard_on_field,
    verify_keyboard_core_on_field,
)

CORE_KIND = KEYBOARD_CORE_KIND


def export_keyboard_layout_core_ltm(
    out_dir: Path,
    *,
    layout_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build immutable keyboard pack: physical, qwerty, jcuken, punct×2."""
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    rep = imprint_split_keyboard_on_field(state, layout_ids=layout_ids)
    lattices = memory_lattices(state)
    ltm_dir = out_dir / "ltm"
    rows: dict[str, dict] = {}
    total_raw = 0
    total_file = 0
    for lid in VK_CORE_LATTICE_IDS:
        lat = lattices.get(lid)
        if not lat:
            continue
        sub = lattice_subdir(lid)
        path = ltm_dir / sub / f"{lid}.ltm"
        info = write_ltm(path, lat, compress=False)
        meta = {k: v for k, v in lat.items() if k not in ("width", "height", "cells")}
        rows[lid] = {**info, "meta": meta}
        total_raw += int(info["raw_bytes"])
        total_file += int(info["file_bytes"])
    manifest = {
        "schema_version": 1,
        "format": "ltm-pack-v0",
        "kind": CORE_KIND,
        "immutable": True,
        "decode_mode": "compose",
        "field_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lattices": rows,
        "totals": {
            "lattice_count": len(rows),
            "mapping_count": rep.get("mapping_count"),
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
        "imprint": rep,
        "verify": rep.get("verify"),
        "locale_map": {
            "qwerty_us": {"lang": "lang.en", "alphabet": L0_LATN_ID, "punct": L0_PUNCT_LATN_ID},
            "jcuken_ru": {"lang": "lang.ru", "alphabet": L0_CYRL_ID, "punct": L0_PUNCT_CYRL_ID},
        },
    }
    ltm_dir.mkdir(parents=True, exist_ok=True)
    (ltm_dir / "pack.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
