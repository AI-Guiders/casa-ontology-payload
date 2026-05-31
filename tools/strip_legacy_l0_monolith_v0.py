#!/usr/bin/env python3
"""Remove L0_grapheme monolith from a store; reimprint immutable alphabet; refresh ltm/l0."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from alphabet_core_v0 import verify_alphabet_on_l0  # type: ignore
from export_ltm_pack_v0 import export_pack  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from grapheme_ingest_v0 import L0_ID_LEGACY, strip_legacy_l0_monolith  # type: ignore
from migrate_l0_grapheme_split_v0 import patch_state_metadata  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore


def _prune_memory_manifest(store_dir: Path) -> list[str]:
    path = store_dir / "memory_manifest.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    stack = data.get("lattice_stack")
    if not isinstance(stack, list):
        return []
    before = len(stack)
    data["lattice_stack"] = [e for e in stack if str(e.get("id") or "") != L0_ID_LEGACY]
    if len(data["lattice_stack"]) == before:
        return []
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ["memory_manifest: dropped L0_grapheme"]


def strip_store(store_dir: Path, *, compact: bool) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    fs = store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(fs))
    def _l2_words(st: dict) -> int:
        from predictor_v0 import l2_lexicon_digest  # type: ignore

        sh = st.get("l2_sharding") or {}
        n = sh.get("indexed_words")
        if n is not None:
            return int(n)
        return len(l2_lexicon_digest(st))

    before_l2 = _l2_words(state)
    before_l0 = sorted(k for k in memory_lattices(state) if k.startswith("L0_grapheme"))

    strip_rep = strip_legacy_l0_monolith(state)
    meta = patch_state_metadata(state, store_dir)
    save_field_state(fs, state, compact=compact)

    ltm_legacy = store_dir / "ltm" / "l0" / f"{L0_ID_LEGACY}.ltm"
    removed_files: list[str] = []
    if ltm_legacy.is_file():
        ltm_legacy.unlink()
        removed_files.append(str(ltm_legacy.relative_to(store_dir)))

    nca_legacy = store_dir / "nca" / L0_ID_LEGACY
    if nca_legacy.is_dir():
        shutil.rmtree(nca_legacy)
        removed_files.append(str(nca_legacy.relative_to(store_dir)))

    ltm_dir = store_dir / "ltm"
    export_pack(
        state,
        ltm_dir,
        store_dir=store_dir,
        lattice_ids=["L0_grapheme_cyrl", "L0_grapheme_latn"],
    )

    manifest_changes = _prune_memory_manifest(store_dir)
    after_l2 = _l2_words(state)
    verify = verify_alphabet_on_l0(state)

    return {
        "store": store_dir.name,
        "before_l0": before_l0,
        "strip": strip_rep,
        "meta": meta,
        "removed_files": removed_files,
        "manifest": manifest_changes,
        "l2_indexed_words_before": before_l2,
        "l2_indexed_words_after": after_l2,
        "alphabet_verify": verify,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Strip L0_grapheme monolith; canonical alphabet on store")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--compact", action="store_true", help="Compact field_state JSON")
    args = p.parse_args()
    compact = args.compact or args.store_dir.name.startswith("sss-")
    rep = strip_store(args.store_dir, compact=compact)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
