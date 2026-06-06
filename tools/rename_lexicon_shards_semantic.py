#!/usr/bin/env python3
"""Rename L2 lexicon shards from numeric ids to dictionary range slugs.

Example: lexicon-ru-00 → lexicon-ru-а-андрейкин (word_lo–word_hi from l2_sharding.letter_ranges).

Touches: ltm/l2/*.ltm, nca/, pack.manifest, nca_train_registry, field_state + agent_field.db.
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
from casa.prisms.memory.lexicon_shard import (
    SHARD_NAMING_CORPUS_RANGE,
    attach_corpus_range_shard_ids,
    build_semantic_l2_rename_map,
    sharding_config,
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


def _apply_sharding_metadata(state: dict, *, locale: str) -> None:
    cfg = sharding_config(state)
    cfg["shard_naming"] = SHARD_NAMING_CORPUS_RANGE
    cfg["locale"] = locale
    cfg["shard_prefix"] = f"lexicon-{locale}-"
    cfg["letter_ranges"] = attach_corpus_range_shard_ids(list(cfg.get("letter_ranges") or []), locale=locale)
    wi = dict(cfg.get("word_index") or {})
    rename = build_semantic_l2_rename_map(cfg, locale=locale)
    cfg["word_index"] = {w: rename.get(str(sid), str(sid)) for w, sid in wi.items()}
    state["l2_sharding"] = cfg


def rename_semantic_shards(
    store_dir: Path,
    *,
    locale: str = "ru",
    dry_run: bool,
    compact: bool,
) -> dict:
    store_dir = store_dir.resolve()
    fs_path = field_state_path(store_dir)
    state = normalize_prisms(load_field_state(fs_path, store_dir=store_dir))
    cfg = sharding_config(state)
    if not cfg.get("letter_ranges"):
        return {"error": "no letter_ranges in l2_sharding; run remigrate_l2_lex first"}

    _apply_sharding_metadata(state, locale=locale)
    rename_map = build_semantic_l2_rename_map(state["l2_sharding"], locale=locale)
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
        _apply_sharding_metadata(state, locale=locale)
        save_field_state(fs_path, state, compact=compact)

    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--locale", default="ru")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--write-memory", action="store_true", help="Regenerate MEMORY.md after rename")
    args = p.parse_args()

    rep = rename_semantic_shards(
        args.store_dir,
        locale=args.locale,
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
