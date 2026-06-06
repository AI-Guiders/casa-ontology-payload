#!/usr/bin/env python3
"""Sync L3 phrase .ltm files with field_state (semantic shard ids).

After rename_phrase_shards_semantic: field/manifest use phrases-{token_lo}-{token_hi},
but ltm/memory/phrase/ may still hold legacy L3_phrase_XX.ltm. This tool re-exports
from field and prunes stale filenames.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.phrase_shard import LEGACY_L3, PHRASES_MONOLITH, l3_phrase_lattice_ids
from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path, ltm_root

_LEGACY_L3_SHARD = re.compile(r"^L3_phrase_\d{2}(\.ltm)?$")
_LEGACY_PHRASES_NUM = re.compile(r"^phrases-\d{2}(\.ltm)?$")


def _phrase_shard_ids(state: dict) -> list[str]:
    skip = {LEGACY_L3, PHRASES_MONOLITH, "phrases"}
    return sorted(
        lid
        for lid in l3_phrase_lattice_ids(state)
        if lid not in skip and lid.startswith("phrases-")
    )


def _stale_ltm_files(phrase_dir: Path) -> list[Path]:
    stale: list[Path] = []
    if not phrase_dir.is_dir():
        return stale
    for path in phrase_dir.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if _LEGACY_L3_SHARD.match(name) or _LEGACY_PHRASES_NUM.match(name):
            stale.append(path)
    return sorted(stale)


def sync_phrase_ltm(
    store_dir: Path,
    *,
    dry_run: bool,
    prune: bool,
) -> dict:
    store_dir = store_dir.resolve()
    fs_path = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs_path, store_dir=store_dir))
    targets = _phrase_shard_ids(state)
    if not targets:
        return {"error": "no semantic phrases-* shard lattices in field_state"}

    ltm_dir = ltm_root(store_dir)
    phrase_dir = ltm_dir / "memory" / "phrase"
    stale = _stale_ltm_files(phrase_dir)

    report: dict = {
        "store": store_dir.name,
        "export_shards": len(targets),
        "stale_ltm": [p.name for p in stale],
        "dry_run": dry_run,
    }

    if dry_run:
        report["would_export"] = targets[:4]
        return report

    manifest_path = ltm_dir / "pack.manifest.json"
    prev: dict = {}
    if manifest_path.is_file():
        try:
            prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}

    manifest = export_pack(
        state,
        ltm_dir,
        store_dir=store_dir,
        lattice_ids=targets,
        include_control=False,
        remigrate_l2=False,
        remigrate_l3=False,
    )

    merged_lattices = dict(prev.get("lattices") or {})
    merged_lattices.update(manifest.get("lattices") or {})
    for old_key in list(merged_lattices):
        if _LEGACY_L3_SHARD.match(old_key + ".ltm") or _LEGACY_PHRASES_NUM.match(old_key + ".ltm"):
            merged_lattices.pop(old_key, None)
    manifest["lattices"] = merged_lattices
    if prev.get("control_lattices"):
        manifest["control_lattices"] = prev["control_lattices"]
    if prev.get("prisms") and manifest.get("prisms"):
        for pid, block in prev["prisms"].items():
            cur = manifest["prisms"].setdefault(pid, {"kind": block.get("kind"), "lattice_ids": []})
            ids = list(cur.get("lattice_ids") or [])
            for lid in block.get("lattice_ids") or []:
                if lid not in ids:
                    ids.append(lid)
            cur["lattice_ids"] = ids
    manifest["l3_sharding"] = state.get("l3_sharding")
    manifest["field_version"] = state.get("field_version")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pruned: list[str] = []
    if prune:
        for path in stale:
            if path.is_file():
                path.unlink()
                pruned.append(path.name)

    report["exported"] = len(manifest.get("lattices") or {})
    report["pruned"] = pruned
    report["sample_paths"] = [
        str((phrase_dir / f"{lid}.ltm").relative_to(store_dir))
        for lid in targets[:2]
        if (phrase_dir / f"{lid}.ltm").is_file()
    ]
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-prune", action="store_true", help="Keep legacy L3_phrase_XX.ltm files")
    args = p.parse_args()

    rep = sync_phrase_ltm(
        args.store_dir,
        dry_run=args.dry_run,
        prune=not args.no_prune,
    )
    if rep.get("error"):
        print("error:", rep["error"])
        raise SystemExit(1)
    mode = "dry-run" if args.dry_run else "done"
    print(f"[{mode}] {rep.get('store')}: export {rep.get('export_shards')} shards")
    if rep.get("stale_ltm"):
        print(f"  stale ltm: {len(rep['stale_ltm'])}")
    if rep.get("pruned"):
        print(f"  pruned: {len(rep['pruned'])}")
    if rep.get("sample_paths"):
        print("  sample:", rep["sample_paths"])


if __name__ == "__main__":
    main()
