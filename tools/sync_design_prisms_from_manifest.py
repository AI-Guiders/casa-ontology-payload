#!/usr/bin/env python3
"""Sync design/prisms/catalog snippets from store ltm/pack.manifest.json (ADR-0012 T12-2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT


def sync_from_manifest(store_dir: Path, *, dry_run: bool = False) -> dict:
    manifest_path = store_dir / "ltm" / "pack.manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    store_id = store_dir.name
    out_dir = REPO_ROOT / "design" / "prisms" / "catalog"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{store_id}.json"
    catalog = {
        "schema_version": "prism_catalog_v1",
        "store_id": store_id,
        "default_content_prism": manifest.get("default_content_prism"),
        "prisms": manifest.get("prisms") or {},
        "lattice_count": (manifest.get("totals") or {}).get("lattice_count"),
        "source_manifest": str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    if dry_run:
        return {"would_write": str(out_path), "prism_count": len(catalog["prisms"])}
    out_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"written": str(out_path), "prism_count": len(catalog["prisms"])}


def main() -> None:
    p = argparse.ArgumentParser(description="Export pack.manifest prisms → design/prisms/catalog/")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    rep = sync_from_manifest(args.store_dir.resolve(), dry_run=args.dry_run)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
