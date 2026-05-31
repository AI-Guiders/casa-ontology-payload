#!/usr/bin/env python3
"""Rebuild field_state.json from store ltm/ (manifest + scan all shard files)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from casa.prisms.memory.boot_core_ltm import merge_alphabet_l0_from_ltm, default_alphabet_core_ltm_dir
from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.memory.grapheme_ingest import migrate_legacy_l0_grapheme
from casa.prisms.shared.import_ltm_pack import import_ltm_dir_scan, import_pack
from casa.prisms.tick.predictor import l2_lexicon_digest
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_layout import field_state_path, ru_lexicon_store


def rebuild_store(
    store_dir: Path,
    *,
    alphabet_ltm: Path | None = None,
    fix_manifest: bool = True,
) -> dict:
    store_dir = store_dir.resolve()
    ltm_dir = store_dir / "ltm"
    fs_path = field_state_path(store_dir)

    if fs_path.is_file():
        bak = fs_path.with_suffix(".json.bak")
        shutil.copy2(fs_path, bak)

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    manifest_rep = import_pack(state, ltm_dir)
    scan_rep = import_ltm_dir_scan(state, ltm_dir)
    mig = migrate_legacy_l0_grapheme(state, default_script="cyrl")
    repo = store_dir.parent.parent.parent
    altm = alphabet_ltm or default_alphabet_core_ltm_dir(root=repo)
    boot = merge_alphabet_l0_from_ltm(state, altm) if (altm / "pack.manifest.json").is_file() else {}

    digest = l2_lexicon_digest(state)
    save_field_state(fs_path, state, compact=True)

    manifest_fix: dict | None = None
    if fix_manifest:
        manifest_fix = export_pack(state, ltm_dir, store_dir=store_dir)

    return {
        "store": store_dir.name,
        "backup": str(fs_path.with_suffix(".json.bak")) if fs_path.with_suffix(".json.bak").is_file() else None,
        "import": manifest_rep,
        "scan": scan_rep,
        "l0_split": mig,
        "alphabet_boot": boot.get("import", {}).get("loaded") if boot else None,
        "l2_headwords": len(digest),
        "manifest_lattices": manifest_fix.get("totals") if manifest_fix else None,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Rebuild field_state from ltm/ scan + alphabet core")
    p.add_argument("--store-dir", type=Path, default=ru_lexicon_store(root=root))
    p.add_argument("--no-manifest-fix", action="store_true")
    args = p.parse_args()

    rep = rebuild_store(args.store_dir, fix_manifest=not args.no_manifest_fix)
    rep["rebuilt_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if rep["l2_headwords"] < 1000:
        raise SystemExit(
            f"rebuild suspicious: only {rep['l2_headwords']} L2 headwords — "
            "copy field_state from lab/agent-stores/sss-afan then remigrate_l2_lex.py"
        )


if __name__ == "__main__":
    main()
