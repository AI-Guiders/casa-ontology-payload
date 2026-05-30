#!/usr/bin/env python3
"""Listen keyboard-layout JSON → L0_vk_map compose + L0_grapheme + export core ltm."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from grapheme_ingest_v0 import L0_ID  # type: ignore
from import_ltm_pack_v0 import import_pack  # type: ignore
from ltm_pack_v0 import lattice_subdir, write_ltm  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore
from input_modality_ingest_v0 import default_input_modality_bundle, ingest_input_modality  # type: ignore
from vk_layout_field_v0 import (  # type: ignore
    L0_VK_MAP_ID,
    compose_index_from_lattice,
    imprint_vk_layouts_on_field,
)


def export_core_ltm(
    out_dir: Path,
    *,
    layout_ids: list[str] | None = None,
    modality_bundle: dict | None = None,
) -> dict:
    state = ensure_cylinders({"schema_version": "multi_cylinder_v1", "field_version": 0})
    imprint_rep = imprint_vk_layouts_on_field(state, layout_ids=layout_ids)
    bundle_path = default_input_modality_bundle()
    modality = modality_bundle or json.loads(bundle_path.read_text(encoding="utf-8"))
    modality_rep = ingest_input_modality(state, modality, ensure_vk_map=False)
    lattices = memory_lattices(state)
    ltm_dir = out_dir / "ltm"
    rows: dict[str, dict] = {}
    total_raw = 0
    total_file = 0

    for lid in (L0_VK_MAP_ID, L0_ID):
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

    idx = compose_index_from_lattice(lattices[L0_VK_MAP_ID])
    manifest = {
        "schema_version": 1,
        "format": "ltm-pack-v0",
        "kind": "core_ltm_vk_layouts_v0",
        "immutable": True,
        "decode_mode": "compose",
        "field_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lattices": rows,
        "totals": {
            "lattice_count": len(rows),
            "mapping_count": len(idx),
            "edge_count": imprint_rep.get("edge_count"),
            "modality_concepts": modality_rep.get("concepts_on_field"),
            "modality_edges": modality_rep.get("edges_placed"),
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
        "input_modality": modality_rep,
    }
    ltm_dir.mkdir(parents=True, exist_ok=True)
    (ltm_dir / "pack.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Ingest VK layouts → field compose + core ltm")
    p.add_argument(
        "--core-out",
        type=Path,
        default=root / "examples/agent-core/vk-layouts-v0",
        help="Export immutable core ltm pack",
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--write", action="store_true")
    args = p.parse_args()

    manifest = export_core_ltm(args.core_out, layout_ids=None)
    print(json.dumps({"export": str(args.core_out), "totals": manifest["totals"]}, ensure_ascii=False, indent=2))

    if args.store_dir:
        store = args.store_dir.resolve()
        fs_path = field_state_path(store)
        if fs_path.is_file():
            state = ensure_cylinders(load_field_state(fs_path))
        else:
            state = ensure_cylinders({"schema_version": "multi_cylinder_v1", "field_version": 0})
        import_pack(state, args.core_out / "ltm", manifest=manifest)
        state.setdefault("store", {})["core_ltm"] = str(args.core_out / "ltm")
        if args.write:
            save_field_state(fs_path, state, compact=True)
        print(json.dumps({"store": str(store), "imported": list(manifest["lattices"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
