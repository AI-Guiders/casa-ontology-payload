#!/usr/bin/env python3
"""Listen input-modality KB → C:/E: tokens on L0_vk_map (explain keyboard/layout to CASA)."""

from __future__ import annotations

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import argparse
import json
from pathlib import Path
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_stack_v0 import _place_token, decode_lattice  # type: ignore
from store_boot_v0 import boot_store  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore
from vk_layout_field_v0 import (  # type: ignore
    L0_VK_MAP_ID,
    L0_VK_PHYSICAL_ID,
    imprint_vk_layouts_on_field,
    vk_physical_concept,
)


def default_input_modality_bundle(*, root: Path | None = None) -> Path:
    base = root or Path(__file__).resolve().parent.parent
    return base / "lab/exp_bilingual_v0/kb-input-modality-vk.v1.json"


def _concept_ids(bundle: dict) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for c in bundle.get("claims") or []:
        cid = str(c.get("concept_id") or "").strip()
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def _graph_edges(bundle: dict) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for e in (bundle.get("graph") or {}).get("edges") or []:
        src = str(e.get("src") or "").strip()
        rel = str(e.get("relation") or "").strip()
        dst = str(e.get("dst") or "").strip()
        if src and rel and dst:
            rows.append((src, rel, dst))
    return rows


def ingest_input_modality(
    state: dict,
    bundle: dict,
    *,
    lattice_id: str = L0_VK_PHYSICAL_ID,
    copies: int = 4,
    ensure_vk_map: bool = True,
) -> dict[str, Any]:
    """Imprint modality concepts + graph edges onto vk lattice (listen, like bukvar/entity hub)."""
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    if ensure_vk_map and lattice_id not in lattices:
        imprint_vk_layouts_on_field(state, ensure_graphemes=True)
        lattices = memory_lattices(state)

    lat = lattices.get(lattice_id)
    if not lat:
        raise KeyError(f"lattice missing: {lattice_id}")

    g = Grid(
        width=int(lat.get("width") or 32),
        height=int(lat.get("height") or 32),
        cells=lat.get("cells") or [],
    )

    concept_count = 0
    for cid in _concept_ids(bundle):
        g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=copies, radius=5)
        concept_count += 1

    edge_count = 0
    for src, rel, dst in _graph_edges(bundle):
        tok = f"E:{src}|{rel}|{dst}"
        g = _place_token(g, tok, tok, copies=max(2, copies // 2), radius=4)
        edge_count += 1

    for ex in bundle.get("exemplars") or []:
        key_id = str(ex.get("key_id") or "").strip()
        layout_id = str(ex.get("layout_id") or "").strip()
        if not key_id:
            continue
        vk_cid = vk_physical_concept(key_id)
        g = _place_token(g, f"C:{vk_cid}", f"C:{vk_cid}", copies=max(2, copies - 1), radius=4)
        if layout_id:
            tok = f"E:{vk_cid}|sample_layout|layout.{layout_id}"
            g = _place_token(g, tok, tok, copies=2, radius=3)
            edge_count += 1

    lat["cells"] = g.cells
    lat.setdefault("listen", {})["input_modality_v0"] = {
        "bundle_id": bundle.get("bundle_id"),
        "concept_count": concept_count,
        "edge_count": edge_count,
    }
    lattices[lattice_id] = lat
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["input_modality"] = {
        "bundle_id": bundle.get("bundle_id"),
        "lattice_id": lattice_id,
        "concept_count": concept_count,
        "edge_count": edge_count,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1

    dec = decode_lattice(lat, min_votes=1)
    on_field = {str(c.get("concept_id") or "") for c in dec.get("concepts") or []}
    expected = set(_concept_ids(bundle))
    missing = sorted(expected - on_field)
    return {
        "lattice_id": lattice_id,
        "bundle_id": bundle.get("bundle_id"),
        "concepts_placed": concept_count,
        "edges_placed": edge_count,
        "concepts_on_field": len(on_field & expected),
        "concepts_missing": missing,
        "lattice_edges": len(dec.get("edges") or []),
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Listen kb-input-modality → L0_vk_map")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--boot-ltm-only", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--copies", type=int, default=4)
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    bundle_path = args.bundle or default_input_modality_bundle(root=root)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    if args.store_dir:
        store = args.store_dir.resolve()
        fs = field_state_path(store)
        if args.boot_ltm_only or not fs.is_file():
            state = boot_store(store, prefer_field_state=False)["state"]
        else:
            state = ensure_prisms(load_field_state(fs))
    else:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    rep = ingest_input_modality(state, bundle, copies=args.copies)
    if args.write and args.store_dir:
        save_field_state(field_state_path(args.store_dir), state, compact=True)
        rep["written"] = str(field_state_path(args.store_dir))
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
