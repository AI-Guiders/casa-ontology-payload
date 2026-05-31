#!/usr/bin/env python3
"""Listen keyboard layouts → split immutable core ltm (physical + QWERTY + JCUKEN + punct)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.import_ltm_pack_v0 import import_pack
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.shared.store_layout_v0 import field_state_path
from casa.prisms.memory.input_modality_ingest_v0 import default_input_modality_bundle, ingest_input_modality
from casa.prisms.memory.keyboard_layout_core_v0 import export_keyboard_layout_core_ltm


def export_core_ltm(
    out_dir: Path,
    *,
    layout_ids: list[str] | None = None,
    modality_bundle: dict | None = None,
) -> dict:
    """Split keyboard core (physical + layouts + punct) + optional modality ingest on field."""
    manifest = export_keyboard_layout_core_ltm(out_dir, layout_ids=layout_ids)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    import_pack(state, out_dir / "ltm", manifest=manifest)
    bundle_path = default_input_modality_bundle()
    modality = modality_bundle or json.loads(bundle_path.read_text(encoding="utf-8"))
    modality_rep = ingest_input_modality(state, modality, ensure_vk_map=False)
    manifest["input_modality"] = modality_rep
    manifest.setdefault("totals", {})["modality_concepts"] = modality_rep.get("concepts_on_field")
    manifest["totals"]["modality_edges"] = modality_rep.get("edges_placed")
    (out_dir / "ltm" / "pack.manifest.json").write_text(
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
        default=root / "lab/agent-core/vk-layouts-v0",
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
            state = ensure_prisms(load_field_state(fs_path))
        else:
            state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        import_pack(state, args.core_out / "ltm", manifest=manifest)
        state.setdefault("store", {})["core_ltm"] = str(args.core_out / "ltm")
        if args.write:
            save_field_state(fs_path, state, compact=True)
        print(json.dumps({"store": str(store), "imported": list(manifest["lattices"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
