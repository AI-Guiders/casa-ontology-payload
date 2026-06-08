#!/usr/bin/env python3
"""Migrate zone/prism/lattice tags (ADR-0067 P11a — dry-run safe)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.prisms.intelligence.zone_prism_map import (
    ZONE_PRISM_MAP_VERSION,
    build_lattice_index,
    load_zone_prism_map,
    shadow_tract_report,
)
from casa.prisms.memory.agent_prism import load_agent_prism
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import ltm_root
from casa.prisms.shared.store_persist import save_runtime_state


def _persist_index(store_dir: Path, state: dict, index: dict[str, Any]) -> dict[str, Any]:
    meta_dir = ltm_root(store_dir) / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    out_path = meta_dir / "zone_prism_map.json"
    payload = {
        "schema_version": ZONE_PRISM_MAP_VERSION,
        "generated_from": "migrate_zone_prism_wire",
        "store": store_dir.name,
        "by_owner_zone": index.get("by_owner_zone"),
        "by_domain": index.get("by_domain"),
        "unknown_lattice_ids": index.get("unknown_lattice_ids"),
        "entries": index.get("entries"),
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    state.setdefault("meta", {})
    state["meta"]["zone_prism_map_version"] = ZONE_PRISM_MAP_VERSION
    state["meta"]["zone_lattice_index"] = {
        str(row["lattice_id"]): {k: v for k, v in row.items() if k != "lattice_id"}
        for row in (index.get("entries") or [])
        if isinstance(row, dict) and row.get("lattice_id")
    }
    save_agent = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)
    return {"path": str(out_path), "save_runtime": save_agent}


def migrate_zone_prism_wire(
    store_dir: Path,
    *,
    map_path: Path | None = None,
    dry_run: bool = True,
    persist: bool = False,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    doc = load_zone_prism_map(map_path)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name
    load_agent_prism(store_dir, state)

    index = build_lattice_index(store_dir, state, doc)
    shadow = shadow_tract_report(index, doc)

    report: dict[str, Any] = {
        "dry_run": dry_run and not persist,
        "store": store_dir.name,
        "zone_prism_map_version": ZONE_PRISM_MAP_VERSION,
        "lattice_count": index.get("lattice_count"),
        "by_owner_zone": index.get("by_owner_zone"),
        "by_domain": index.get("by_domain"),
        "by_mutability": index.get("by_mutability"),
        "unknown_count": len(index.get("unknown_lattice_ids") or []),
        "unknown_sample": (index.get("unknown_lattice_ids") or [])[:12],
        "immutable_sample": [
            row.get("lattice_id")
            for row in (index.get("entries") or [])
            if isinstance(row, dict) and row.get("mutability") == "immutable"
        ][:12],
        "shadow_tract": shadow,
        "field_version": int(state.get("field_version") or 0),
    }

    if persist and not dry_run:
        report["persist"] = _persist_index(store_dir, state, index)
    elif persist and dry_run:
        report["persist_skipped"] = "dry_run"

    report["index"] = index if dry_run else None
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Zone/prism/lattice wire migrate (ADR-0067 P11a)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--map",
        type=Path,
        default=REPO_ROOT / "design" / "zone-prism-map.v1.json",
        help="zone-prism-map v2 JSON",
    )
    p.add_argument("--dry-run", action="store_true", help="report only (default when --persist omitted)")
    p.add_argument("--persist", action="store_true", help="write ltm/meta/zone_prism_map.json + meta index")
    args = p.parse_args()

    dry = not args.persist
    rep = migrate_zone_prism_wire(
        args.store_dir,
        map_path=args.map,
        dry_run=dry,
        persist=args.persist,
    )
    summary = {k: v for k, v in rep.items() if k != "index"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if dry and rep.get("index"):
        entries = rep["index"].get("entries") or []
        if entries:
            print("\n# sample entries (first 8)")
            print(json.dumps(entries[:8], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
