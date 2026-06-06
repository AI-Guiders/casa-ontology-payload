#!/usr/bin/env python3
"""Rename L3 phrase shards from numeric ids to field-token range slugs.

Example: L3_phrase_07 → phrases-lang.word.водкина-lang.word.всемирный
(token_lo–token_hi from l3_sharding.token_ranges; shard index stays in metadata only).

Touches: ltm/memory/phrase/*.ltm, nca/, pack.manifest, nca_train_registry, field_state + agent_field.db.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.prism_wire import normalize_prisms
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.phrase_shard import (
    L3_SHARD_PREFIX,
    SHARD_NAMING_TOKEN_RANGE,
    attach_token_range_shard_ids,
    build_semantic_l3_rename_map,
    infer_token_ranges_from_shards,
    phrase_sharding_config,
)
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.migrate_lattice_ids_v1 import (
    migrate_field_state,
    migrate_ltm_files,
    migrate_manifest,
    migrate_nca_dirs,
    migrate_registry,
)
from casa.prisms.shared.store_layout import field_state_path, use_compact_field_state


def _apply_sharding_metadata(state: dict) -> None:
    cfg = phrase_sharding_config(state)
    cfg["shard_naming"] = SHARD_NAMING_TOKEN_RANGE
    cfg["shard_prefix"] = "phrases-"
    cfg["token_ranges"] = attach_token_range_shard_ids(list(cfg.get("token_ranges") or []))
    ti = dict(cfg.get("token_index") or {})
    rename = build_semantic_l3_rename_map(cfg)
    cfg["token_index"] = {tok: rename.get(str(sid), str(sid)) for tok, sid in ti.items()}
    state["l3_sharding"] = cfg


def _ensure_token_ranges(state: dict) -> None:
    cfg = phrase_sharding_config(state)
    if cfg.get("token_ranges"):
        return
    lats = memory_lattices(state)
    has_shards = any(lid.startswith(L3_SHARD_PREFIX) for lid in lats)
    if not has_shards:
        return
    cfg["token_ranges"] = infer_token_ranges_from_shards(state)
    state["l3_sharding"] = cfg


def rename_semantic_phrase_shards(
    store_dir: Path,
    *,
    dry_run: bool,
    compact: bool,
) -> dict:
    store_dir = store_dir.resolve()
    fs_path = field_state_path(store_dir)
    state = normalize_prisms(load_field_state(fs_path, store_dir=store_dir))
    state = ensure_prisms(state)
    _ensure_token_ranges(state)
    cfg = phrase_sharding_config(state)
    if not cfg.get("token_ranges"):
        return {"error": "no token_ranges and no L3_phrase_XX shards to infer from"}

    _apply_sharding_metadata(state)
    rename_map = build_semantic_l3_rename_map(state["l3_sharding"])
    if not rename_map:
        return {"renamed": 0, "reason": "nothing to rename"}

    report: dict = {
        "store": store_dir.name,
        "renamed": len(rename_map),
        "sample": dict(list(rename_map.items())[:4]),
        "actions": [],
    }
    report["actions"].extend(migrate_ltm_files(store_dir, rename_map, dry_run=dry_run))
    report["actions"].extend(migrate_manifest(store_dir, rename_map, dry_run=dry_run))
    report["actions"].extend(migrate_nca_dirs(store_dir, rename_map, dry_run=dry_run))
    report["actions"].extend(migrate_registry(store_dir, rename_map, dry_run=dry_run))
    report["actions"].extend(
        migrate_field_state(store_dir, rename_map, dry_run=dry_run, compact=compact)
    )

    if not dry_run:
        state = normalize_prisms(load_field_state(fs_path, store_dir=store_dir))
        _ensure_token_ranges(state)
        _apply_sharding_metadata(state)
        save_field_state(fs_path, state, compact=compact)

    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--write-memory", action="store_true", help="Regenerate MEMORY.md after rename")
    args = p.parse_args()

    rep = rename_semantic_phrase_shards(
        args.store_dir,
        dry_run=args.dry_run,
        compact=args.compact or use_compact_field_state(args.store_dir),
    )
    mode = "dry-run" if args.dry_run else "done"
    print(f"[{mode}] {rep.get('store')}: {rep.get('renamed', 0)} ids")
    if rep.get("error"):
        print("error:", rep["error"])
        raise SystemExit(1)
    for line in rep.get("actions") or []:
        print(" ", line)
    if rep.get("sample"):
        print("sample:", json.dumps(rep["sample"], ensure_ascii=False, indent=2))

    if args.write_memory and not args.dry_run:
        from casa.prisms.memory.memory_manifest import build_manifest, render_memory_md
        from casa.prisms.memory.memory_prisms import ensure_prisms

        fs = field_state_path(args.store_dir)
        st = ensure_prisms(load_field_state(fs, store_dir=args.store_dir))
        manifest = build_manifest(args.store_dir, st)
        args.store_dir.joinpath("memory_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        args.store_dir.joinpath("MEMORY.md").write_text(render_memory_md(manifest), encoding="utf-8")
        print("wrote MEMORY.md")


if __name__ == "__main__":
    main()
