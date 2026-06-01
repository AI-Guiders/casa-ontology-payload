#!/usr/bin/env python3
"""Export memory lattices from field_state.json → store/ltm/*.ltm."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.ltm_pack import lattice_subdir, write_ltm
from casa.prisms.shared.store_paths_v1 import ltm_write_targets, manifest_layout_block
from casa.prisms.control.cylinders import control_lattices, has_control_stack
from casa.domain.field_state import FieldState
from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms, memory_lattices
from casa.prisms.memory.lexicon_shard import l2_en_word_lattice_ids, l2_lexicon_lattice_ids, l2_word_lattice_ids
from casa.prisms.memory.prism_spawn import list_content_prism_ids, list_control_prism_ids
from casa.domain.prism_ids import PRISM_CONTROL, PRISM_MEMORY
from casa.domain.prism_wire import prism_kind, prism_router
from casa.prisms.shared.store_layout import nca_train_registry_path, rel_to_repo


def _lattice_meta(lat: dict) -> dict[str, Any]:
    skip = {"width", "height", "cells"}
    return {k: v for k, v in lat.items() if k not in skip}


def _rel_nca_block(nca: dict | None) -> dict | None:
    """Copy the state NCA block with model paths rewritten repo-relative."""
    if not nca:
        return nca
    out = dict(nca)
    models = nca.get("models")
    if isinstance(models, dict):
        out["models"] = {lid: rel_to_repo(p) for lid, p in models.items()}
    if isinstance(nca.get("model_path"), str):
        out["model_path"] = rel_to_repo(nca["model_path"])
    return out


def _rel_registry(reg: dict) -> dict:
    """Copy a train registry with model paths rewritten repo-relative."""
    out = dict(reg)
    lattices = reg.get("lattices")
    if isinstance(lattices, dict):
        out["lattices"] = {
            lid: {**e, "model_path": rel_to_repo(e.get("model_path"))} for lid, e in lattices.items()
        }
    return out


def control_lattice_ids(state: dict) -> list[str]:
    if not has_control_stack(state):
        return []
    return sorted(control_lattices(state).keys())


def iter_profile_lattice_exports(
    state: dict,
    *,
    content_prism_ids: list[str] | None = None,
    lattice_ids: list[str] | None = None,
    include_control: bool = True,
) -> list[tuple[str, str, dict]]:
    """(prism_id, lattice_id, lattice) for shipped compact persist."""
    state = ensure_prisms(state)
    items: list[tuple[str, str, dict]] = []
    if lattice_ids is not None:
        merged: dict[str, dict] = {**memory_lattices(state)}
        if include_control and has_control_stack(state):
            merged = {**merged, **control_lattices(state)}
        for lid in lattice_ids:
            lat = merged.get(lid)
            if lat:
                pid = PRISM_CONTROL if str(lid).startswith("lattice_") else PRISM_MEMORY
                items.append((pid, lid, lat))
        return items

    pids = content_prism_ids if content_prism_ids is not None else list_content_prism_ids(state)
    for pid in pids:
        for lid, lat in sorted(content_prism_lattices(state, pid).items()):
            items.append((pid, lid, lat))
    if include_control:
        for cpid in list_control_prism_ids(state):
            if cpid == PRISM_CONTROL and has_control_stack(state):
                for lid, lat in sorted(control_lattices(state).items()):
                    items.append((PRISM_CONTROL, lid, lat))
            elif cpid != PRISM_CONTROL:
                for lid, lat in sorted(content_prism_lattices(state, cpid).items()):
                    items.append((cpid, lid, lat))
    return items


def export_field_state(
    field: FieldState,
    out_dir: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Domain entry: export shipped ltm from :class:`FieldState` (ADR-0020 M2)."""
    return export_pack(field.wire, out_dir, **kwargs)


def export_pack(
    state: dict,
    out_dir: Path,
    *,
    store_dir: Path | None = None,
    lattice_ids: list[str] | None = None,
    content_prism_ids: list[str] | None = None,
    include_control: bool = True,
    compress: bool = False,
    remigrate_l2: bool = True,
    remigrate_l3: bool = True,
    skip_vocab_over: int | None = None,
    progress: bool = False,
    parallel_writes: int = 0,
) -> dict[str, Any]:
    from casa.prisms.shared.migrate_progress import resolve_parallel_workers

    field = FieldState.bind(state)
    state = field.wire
    _ = field.catalog  # ensure prism catalog normalized (ADR-0020 M2)
    io_workers = resolve_parallel_workers(parallel_writes)

    def _word_progress(done: int, total: int, shard: str) -> None:
        if progress:
            from casa.prisms.shared.migrate_progress import progress as _prog

            _prog(f"  remigrate words {done}/{total} (last shard {shard})")

    def _token_progress(done: int, total: int, shard: str) -> None:
        if progress:
            from casa.prisms.shared.migrate_progress import progress as _prog

            _prog(f"  remigrate L3 tokens {done}/{total} (last shard {shard})")

    l2_remigrate_report = None
    if remigrate_l2 and lattice_ids is None:
        from casa.prisms.memory.l2_remigrate import ensure_l2_sharded_for_export

        l2_remigrate_report = ensure_l2_sharded_for_export(
            state,
            on_word_progress=_word_progress if progress else None,
        )
    l3_remigrate_report = None
    if remigrate_l3 and lattice_ids is None:
        from casa.prisms.memory.l3_remigrate import ensure_l3_sharded_for_export

        l3_remigrate_report = ensure_l3_sharded_for_export(
            state,
            on_token_progress=_token_progress if progress else None,
            parallel_workers=io_workers,
        )
    nca_block = _rel_nca_block(state.get("nca"))
    exports = list(
        iter_profile_lattice_exports(
            state,
            content_prism_ids=content_prism_ids,
            lattice_ids=lattice_ids,
            include_control=include_control,
        )
    )
    if progress:
        from casa.prisms.shared.migrate_progress import progress as _prog

        _prog(f"  export ltm: {len(exports)} lattices")
    rows: dict[str, Any] = {}
    prism_index: dict[str, dict[str, Any]] = {}
    skipped_vocab: list[dict[str, Any]] = []
    total_raw = 0
    total_file = 0

    def _export_one(i: int, pid: str, lid: str, lat: dict) -> dict[str, Any]:
        if skip_vocab_over is not None:
            from casa.prisms.memory.lexicon_shard import lattice_vocab_size

            vocab_n = lattice_vocab_size(lat)
            if vocab_n > skip_vocab_over:
                if progress:
                    from casa.prisms.shared.migrate_progress import progress as _prog

                    _prog(f"  skip {i}/{len(exports)} {pid}/{lid} vocab={vocab_n} > {skip_vocab_over}")
                return {
                    "skip": {
                        "prism_id": pid,
                        "lattice_id": lid,
                        "vocab": vocab_n,
                        "limit": skip_vocab_over,
                        "reason": "ltm_v0_u16_vocab_cap",
                    }
                }
        if progress:
            from casa.prisms.shared.migrate_progress import progress as _prog

            _prog(f"  write {i}/{len(exports)} {pid}/{lid}")
        primary, _aliases = ltm_write_targets(out_dir, lid)
        info = write_ltm(primary, lat, compress=compress)
        try:
            store_rel = primary.relative_to(out_dir.parent).as_posix()
        except ValueError:
            store_rel = rel_to_repo(primary)
        meta = {**_lattice_meta(lat), "prism_id": pid}
        return {
            "lid": lid,
            "pid": pid,
            "info": info,
            "entry": {"path": store_rel, "prism_id": pid, "meta": meta},
        }

    def _apply_export_result(result: dict[str, Any]) -> None:
        nonlocal total_raw, total_file
        if "skip" in result:
            skipped_vocab.append(result["skip"])
            return
        lid = result["lid"]
        pid = result["pid"]
        info = result["info"]
        entry = result["entry"]
        rows[lid] = {**info, **entry}
        prism_index.setdefault(pid, {"kind": prism_kind(state, pid), "lattice_ids": []})
        if lid not in prism_index[pid]["lattice_ids"]:
            prism_index[pid]["lattice_ids"].append(lid)
        total_raw += int(info["raw_bytes"])
        total_file += int(info["file_bytes"])

    if io_workers >= 2 and len(exports) >= 2:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=io_workers) as pool:
            futures = [
                pool.submit(_export_one, i, pid, lid, lat)
                for i, (pid, lid, lat) in enumerate(exports, 1)
            ]
            for fut in as_completed(futures):
                _apply_export_result(fut.result())
    else:
        for i, (pid, lid, lat) in enumerate(exports, 1):
            _apply_export_result(_export_one(i, pid, lid, lat))

    router = prism_router(state)
    manifest = {
        "schema_version": 1,
        "format": "ltm-pack",
        **manifest_layout_block(),
        "l2_remigrate": l2_remigrate_report,
        "l3_remigrate": l3_remigrate_report,
        "field_version": state.get("field_version"),
        "l3_sharding": state.get("l3_sharding"),
        "updated_at": state.get("updated_at"),
        "default_content_prism": router.get("default_content_prism") or PRISM_MEMORY,
        "prisms": prism_index,
        "lattices": rows,
        "l2_sharding": state.get("l2_sharding"),
        "nca": nca_block,
        "totals": {
            "lattice_count": len(rows),
            "content_prism_count": len(prism_index),
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
    }
    if skipped_vocab:
        manifest["skipped_vocab_lattices"] = skipped_vocab
    if store_dir is not None:
        reg_path = nca_train_registry_path(store_dir)
        if reg_path.is_file():
            manifest["nca_train_registry"] = _rel_registry(
                json.loads(reg_path.read_text(encoding="utf-8"))
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Export compact ltm/ pack from field_state")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None, help="Default: <store>/ltm")
    p.add_argument("--layer", default="all", help="L2 | L1 | L0 | L3 | all")
    p.add_argument("--compress", action="store_true")
    args = p.parse_args()

    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    out_dir = args.out or (args.store_dir / "ltm")
    if args.layer == "all":
        manifest = export_pack(state, out_dir, store_dir=args.store_dir, compress=args.compress)
    else:
        lattices = memory_lattices(state)
        targets: list[str] = []
        if args.layer == "L2":
            targets.extend(l2_lexicon_lattice_ids(state))
            if "L2_word" in lattices and "L2_word" not in targets:
                targets.append("L2_word")
        if args.layer == "L1" and "L1_syllable" in lattices:
            targets.append("L1_syllable")
        if args.layer == "L0":
            for lid in ("L0_grapheme_cyrl", "L0_grapheme_latn"):
                if lid in lattices:
                    targets.append(lid)
        if args.layer == "L3" and "L3_phrase" in lattices:
            targets.append("L3_phrase")
        targets = list(dict.fromkeys(targets))
        manifest = export_pack(
            state, out_dir, store_dir=args.store_dir, lattice_ids=targets, compress=args.compress
        )
    print(json.dumps(manifest["totals"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
