#!/usr/bin/env python3
"""Rename legacy lattice ids (L*, F*, H*, lattice_*) → v1 kebab canonical.

Structural rename only — **no NCA retrain**. Weights in model.pt stay valid; paths update.

Map: design/lattice-id-map.v1.json (migrate-only; runtime uses v1 ids directly).

**Do not run while `train_memory_nca_shards.py` / CUDA train is active** — race on nca/ dirs.

Touches: ltm/*.ltm, pack.manifest.json, nca/<id>/ dirs, nca_train_registry, field_state.json.
"""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.ltm_pack import lattice_subdir
from casa.domain.prism_wire import normalize_prisms, prism_control, prism_hippo, prism_memory
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.shared.store_layout import field_state_path, ltm_root, nca_root, nca_train_registry_path, use_compact_field_state

_MAP_PATH = REPO_ROOT / "design" / "lattice-id-map.v1.json"

_LTM_SUFFIXES = (".ltm.zst", ".ltm.gz", ".ltm")


def _legacy_to_v1(lattice_id: str) -> str:
    lid = str(lattice_id)
    doc = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    fixed = doc.get("legacy_to_v1") or {}
    if lid in fixed:
        return str(fixed[lid])
    for rule in doc.get("pattern_legacy_to_v1") or []:
        m = re.fullmatch(str(rule["match"]), lid)
        if m:
            return m.expand(str(rule["replace"]))
    return lid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _v1_id(lattice_id: str) -> str:
    return _legacy_to_v1(str(lattice_id))


def _needs_rename(lattice_id: str) -> bool:
    return _v1_id(lattice_id) != str(lattice_id)


def build_rename_map(ids: set[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for lid in sorted(ids):
        new = _v1_id(lid)
        if new != lid:
            mapping[lid] = new
    if "H1_surface" in ids and "H0_episode" in mapping:
        del mapping["H0_episode"]
    return mapping


def discover_lattice_ids(store_dir: Path) -> set[str]:
    found: set[str] = set()
    ltm = ltm_root(store_dir)
    manifest_path = ltm / "pack.manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        found.update((manifest.get("lattices") or {}).keys())
        found.update((manifest.get("control_lattices") or {}).keys())

    for sub in ("l0", "l1", "l2", "l3", "h0", "lat", "ctrl"):
        subdir = ltm / sub
        if not subdir.is_dir():
            continue
        for path in subdir.iterdir():
            if not path.is_file():
                continue
            name = path.name
            for suf in _LTM_SUFFIXES:
                if name.endswith(suf):
                    found.add(name[: -len(suf)])
                    break

    nca = nca_root(store_dir)
    if nca.is_dir():
        for child in nca.iterdir():
            if child.is_dir():
                found.add(child.name)

    reg_path = nca_train_registry_path(store_dir)
    if reg_path.is_file():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        found.update((reg.get("lattices") or {}).keys())

    fs_path = field_state_path(store_dir)
    if fs_path.is_file():
        state = normalize_prisms(load_field_state(fs_path))
        found.update(memory_lattices(state).keys())
        found.update(prism_control(state).get("lattices", {}).keys())
        found.update(prism_hippo(state).get("lattices", {}).keys())
        sh = state.get("l2_sharding") or {}
        for key in ("legacy_lattice",):
            if sh.get(key):
                found.add(str(sh[key]))
        en = sh.get("en") or {}
        if en.get("legacy_lattice"):
            found.add(str(en["legacy_lattice"]))

    return found


def _rewrite_strings(obj: Any, rename_map: dict[str, str]) -> Any:
    if isinstance(obj, str):
        s = obj
        for old, new in sorted(rename_map.items(), key=lambda kv: -len(kv[0])):
            if old in s:
                s = s.replace(old, new)
        return s
    if isinstance(obj, list):
        return [_rewrite_strings(x, rename_map) for x in obj]
    if isinstance(obj, dict):
        return {k: _rewrite_strings(v, rename_map) for k, v in obj.items()}
    return obj


def _rename_dict_keys(d: dict[str, Any], rename_map: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        nk = rename_map.get(str(k), str(k))
        if nk in out and nk != k:
            raise ValueError(f"key collision after rename: {k!r} → {nk!r}")
        out[nk] = v
    return out


def _ltm_file_for(ltm_dir: Path, lattice_id: str) -> Path | None:
    for subdir in ("l0", "l1", "l2", "l3", "h0", "lat", "ctrl"):
        d = ltm_dir / subdir
        if not d.is_dir():
            continue
        for path in d.iterdir():
            if not path.is_file():
                continue
            stem = path.name
            for ext in _LTM_SUFFIXES:
                if stem.endswith(ext):
                    if stem[: -len(ext)] == lattice_id:
                        return path
                    break
    return None


def _ltm_target_path(ltm_dir: Path, lattice_id: str, *, source: Path) -> Path:
    sub = lattice_subdir(lattice_id)
    suffix = ""
    for ext in _LTM_SUFFIXES:
        if source.name.endswith(ext):
            suffix = ext
            break
    if not suffix:
        suffix = ".ltm"
    return ltm_dir / sub / f"{lattice_id}{suffix}"


def migrate_ltm_files(
    store_dir: Path,
    rename_map: dict[str, str],
    *,
    dry_run: bool,
) -> list[str]:
    ltm_dir = ltm_root(store_dir)
    actions: list[str] = []
    for old, new in sorted(rename_map.items()):
        src = _ltm_file_for(ltm_dir, old)
        if src is None:
            continue
        dst = _ltm_target_path(ltm_dir, new, source=src)
        if src.resolve() == dst.resolve():
            continue
        if dst.exists() and not src.exists():
            continue
        actions.append(f"ltm {src.relative_to(store_dir)} → {dst.relative_to(store_dir)}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                raise FileExistsError(f"target exists: {dst}")
            os.replace(src, dst)
    return actions


def migrate_manifest(store_dir: Path, rename_map: dict[str, str], *, dry_run: bool) -> list[str]:
    ltm_dir = ltm_root(store_dir)
    manifest_path = ltm_dir / "pack.manifest.json"
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    before = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    lattices = _rename_dict_keys(manifest.get("lattices") or {}, rename_map)
    for lid, entry in lattices.items():
        if not isinstance(entry, dict):
            continue
        src = _ltm_file_for(ltm_dir, lid)
        if src is not None:
            entry["path"] = str(src.resolve())

    manifest["lattices"] = lattices
    if manifest.get("control_lattices"):
        manifest["control_lattices"] = _rename_dict_keys(manifest["control_lattices"], rename_map)

    if isinstance(manifest.get("l2_sharding"), dict):
        sh = manifest["l2_sharding"]
        if sh.get("legacy_lattice") in rename_map:
            sh["legacy_lattice"] = rename_map[str(sh["legacy_lattice"])]
        if sh.get("shard_prefix") in rename_map:
            sh["shard_prefix"] = rename_map[str(sh["shard_prefix"])]
        elif sh.get("shard_prefix") == "L2_word_":
            sh["shard_prefix"] = "lexicon-ru-"
        manifest["l2_sharding"] = _rewrite_strings(sh, rename_map)
    manifest["lattice_naming"] = {"version": 1, "migrated_at": _now_iso()}
    after = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    actions: list[str] = []
    if before != after:
        actions.append(f"manifest {manifest_path.name} ({len(rename_map)} id map)")
        if not dry_run:
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return actions


def migrate_nca_dirs(store_dir: Path, rename_map: dict[str, str], *, dry_run: bool) -> list[str]:
    nca = nca_root(store_dir)
    if not nca.is_dir():
        return []
    actions: list[str] = []
    for old, new in sorted(rename_map.items()):
        src = nca / old.replace("/", "_")
        dst = nca / new.replace("/", "_")
        if not src.is_dir():
            continue
        if dst.exists() and not src.exists():
            continue
        actions.append(f"nca {src.name}/ → {dst.name}/")
        if not dry_run:
            if dst.exists():
                raise FileExistsError(f"nca target exists: {dst}")
            os.replace(src, dst)
            report = dst / "report.json"
            if report.is_file():
                rep = json.loads(report.read_text(encoding="utf-8"))
                rep = _rewrite_strings(rep, rename_map)
                report.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return actions


def migrate_registry(store_dir: Path, rename_map: dict[str, str], *, dry_run: bool) -> list[str]:
    reg_path = nca_train_registry_path(store_dir)
    if not reg_path.is_file():
        return []
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    before = json.dumps(reg, ensure_ascii=False, sort_keys=True)
    reg["lattices"] = _rename_dict_keys(reg.get("lattices") or {}, rename_map)
    reg = _rewrite_strings(reg, rename_map)
    reg["updated_at"] = _now_iso()
    after = json.dumps(reg, ensure_ascii=False, sort_keys=True)
    actions: list[str] = []
    if before != after:
        actions.append(f"registry {reg_path.name}")
        if not dry_run:
            reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return actions


def migrate_field_state(store_dir: Path, rename_map: dict[str, str], *, dry_run: bool, compact: bool) -> list[str]:
    fs_path = field_state_path(store_dir)
    if not fs_path.is_file():
        return []
    state = normalize_prisms(load_field_state(fs_path))
    before = json.dumps(state, ensure_ascii=False, sort_keys=True)

    mem = prism_memory(state)
    mem["lattices"] = _rename_dict_keys(mem.get("lattices") or {}, rename_map)
    if mem.get("active_lattice") in rename_map:
        mem["active_lattice"] = rename_map[str(mem["active_lattice"])]

    hip = prism_hippo(state)
    hip["lattices"] = _rename_dict_keys(hip.get("lattices") or {}, rename_map)
    for ep in hip.get("episodes") or []:
        if isinstance(ep, dict) and ep.get("lattice_id") in rename_map:
            ep["lattice_id"] = rename_map[str(ep["lattice_id"])]

    ctrl = prism_control(state)
    ctrl["lattices"] = _rename_dict_keys(ctrl.get("lattices") or {}, rename_map)

    sss = state.setdefault("sss", {})
    if sss.get("lattices"):
        sss["lattices"] = _rename_dict_keys(sss["lattices"], rename_map)
    if sss.get("active_lattice") in rename_map:
        sss["active_lattice"] = rename_map[str(sss["active_lattice"])]

    sn = state.get("sn") or {}
    if sn.get("active_lattice") in rename_map:
        sn["active_lattice"] = rename_map[str(sn["active_lattice"])]
        state["sn"] = sn

    if state.get("l2_sharding"):
        sh = dict(state["l2_sharding"])
        if sh.get("legacy_lattice") in rename_map:
            sh["legacy_lattice"] = rename_map[str(sh["legacy_lattice"])]
        if sh.get("shard_prefix") == "L2_word_":
            sh["shard_prefix"] = "words-ru-"
        en = sh.get("en")
        if isinstance(en, dict) and en.get("shard_prefix") == "L2_en_word_":
            en = dict(en)
            en["shard_prefix"] = "words-en-"
            sh["en"] = en
        state["l2_sharding"] = _rewrite_strings(sh, rename_map)

    state = _rewrite_strings(state, rename_map)
    state["lattice_naming_version"] = 1
    after = json.dumps(state, ensure_ascii=False, sort_keys=True)
    actions: list[str] = []
    if before != after:
        actions.append(f"field_state.json")
        if not dry_run:
            save_field_state(fs_path, state, compact=compact)
    return actions


def migrate_store(
    store_dir: Path,
    *,
    dry_run: bool,
    skip_field_state: bool,
    skip_nca: bool,
    compact: bool,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    ids = discover_lattice_ids(store_dir)
    rename_map = build_rename_map(ids)
    if not rename_map:
        return {"store": store_dir.name, "renamed": 0, "actions": [], "skipped": "already v1"}

    report: dict[str, Any] = {
        "store": store_dir.name,
        "renamed": len(rename_map),
        "map_sample": dict(list(rename_map.items())[:5]),
        "actions": [],
    }
    report["actions"].extend(migrate_ltm_files(store_dir, rename_map, dry_run=dry_run))
    report["actions"].extend(migrate_manifest(store_dir, rename_map, dry_run=dry_run))
    if not skip_nca:
        report["actions"].extend(migrate_nca_dirs(store_dir, rename_map, dry_run=dry_run))
        report["actions"].extend(migrate_registry(store_dir, rename_map, dry_run=dry_run))
    if not skip_field_state:
        report["actions"].extend(
            migrate_field_state(store_dir, rename_map, dry_run=dry_run, compact=compact)
        )
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate lattice ids legacy → v1 (no NCA retrain)")
    p.add_argument("--store-dir", type=Path, help="Single agent store directory")
    p.add_argument("--stores-root", type=Path, default=Path("lab/agent-stores"))
    p.add_argument("--dry-run", action="store_true", help="Print planned renames only")
    p.add_argument("--skip-field-state", action="store_true", help="ltm + manifest + nca paths only")
    p.add_argument("--skip-nca", action="store_true", help="Do not rename nca/ or registry")
    p.add_argument("--compact", action="store_true", help="Compact JSON for large field_state")
    args = p.parse_args()

    stores: list[Path] = []
    if args.store_dir:
        stores.append(args.store_dir)
    else:
        root = args.stores_root
        if not root.is_dir():
            raise SystemExit(f"stores root missing: {root}")
        stores = sorted(d for d in root.iterdir() if d.is_dir() and (d / "ltm").is_dir())

    total = 0
    for store in stores:
        rep = migrate_store(
            store,
            dry_run=args.dry_run,
            skip_field_state=args.skip_field_state,
            skip_nca=args.skip_nca,
            compact=args.compact or use_compact_field_state(store),
        )
        n = rep.get("renamed") or 0
        total += n
        mode = "dry-run" if args.dry_run else "done"
        print(f"[{mode}] {rep['store']}: {n} ids, {len(rep.get('actions') or [])} actions")
        for line in (rep.get("actions") or [])[:8]:
            print(f"  {line}")
        if len(rep.get("actions") or []) > 8:
            print(f"  … +{len(rep['actions']) - 8} more")
    print(f"stores={len(stores)} total_ids={total}")


if __name__ == "__main__":
    main()
