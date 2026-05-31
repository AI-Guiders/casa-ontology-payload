#!/usr/bin/env python3
"""Rewrite absolute machine paths in tracked store manifests to repo-relative.

The careful half of the P0 abs-path sanitation (open-source-readiness-and-tech-debt):
``nca_train_registry.json`` (``model_path``) and ``memory_manifest.json``
(``store_path`` + ``lattice_stack[].nca_model``) embed absolute Windows drive paths. These fields are bookkeeping only -- model loading resolves via
store-relative fallback (see nca_registry.model_path_for_lattice) -- so
rewriting them to repo-relative is safe and stops the leak. The matching writer
fixes (store_layout.rel_to_repo) keep regenerated files clean.

    python scripts/sanitize_store_manifests.py            # all stores, write
    python scripts/sanitize_store_manifests.py --check    # report only, exit 1 if dirty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANCHOR = "casa-ontology-payload"


def _rel(value: str) -> str:
    """Repo-relative POSIX path from an absolute (or already-relative) string."""
    norm = value.replace("\\", "/")
    marker = f"{ANCHOR}/"
    idx = norm.find(marker)
    if idx != -1:
        return norm[idx + len(marker):]
    return norm


def _looks_absolute(value: str | None) -> bool:
    return isinstance(value, str) and (ANCHOR in value.replace("\\", "/") and (":/" in value.replace("\\", "/") or ":\\" in value))


def sanitize_registry(path: Path, *, write: bool) -> int:
    reg = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for entry in (reg.get("lattices") or {}).values():
        mp = entry.get("model_path")
        if _looks_absolute(mp):
            entry["model_path"] = _rel(mp)
            changed += 1
    if changed and write:
        path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def sanitize_memory_manifest(path: Path, *, write: bool) -> int:
    man = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    if _looks_absolute(man.get("store_path")):
        man["store_path"] = _rel(man["store_path"])
        changed += 1
    for layer in man.get("lattice_stack") or []:
        nm = layer.get("nca_model")
        if _looks_absolute(nm):
            layer["nca_model"] = _rel(nm)
            changed += 1
    if changed and write:
        path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def _store_rel(value: str, store_id: str) -> str:
    """Path relative to the store dir (``ltm/<sub>/<lid>.ltm``) from an absolute one."""
    norm = value.replace("\\", "/")
    marker = f"/{store_id}/"
    idx = norm.find(marker)
    if idx != -1:
        return norm[idx + len(marker):]
    return _rel(norm)


def sanitize_pack_manifest(path: Path, store_id: str, *, write: bool) -> int:
    """ltm/pack.manifest.json: per-lattice ``path`` + bookkeeping NCA fields.

    ``lattices[].path`` is read at boot but resolved robustly (store-relative
    + a CWD-independent glob fallback in import_ltm_pack._resolve_ltm_path),
    so rewriting absolute paths to store-relative is safe. ``nca.models`` and the
    embedded ``nca_train_registry`` are bookkeeping only.
    """
    man = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for entry in (man.get("lattices") or {}).values():
        if isinstance(entry, dict) and _looks_absolute(entry.get("path")):
            entry["path"] = _store_rel(entry["path"], store_id)
            changed += 1
    nca = man.get("nca") or {}
    models = nca.get("models") or {}
    for lid, mp in list(models.items()):
        if _looks_absolute(mp):
            models[lid] = _rel(mp)
            changed += 1
    if _looks_absolute(nca.get("model_path")):
        nca["model_path"] = _rel(nca["model_path"])
        changed += 1
    for entry in ((man.get("nca_train_registry") or {}).get("lattices") or {}).values():
        mp = entry.get("model_path")
        if _looks_absolute(mp):
            entry["model_path"] = _rel(mp)
            changed += 1
    if changed and write:
        path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def main() -> int:
    p = argparse.ArgumentParser(description="Sanitize abs paths in store manifests (P0)")
    p.add_argument("--check", action="store_true", help="report only; exit 1 if any abs path remains")
    args = p.parse_args()
    write = not args.check

    total = 0

    def _report(f: Path, n: int) -> None:
        nonlocal total
        if n:
            total += n
            verb = "would fix" if args.check else "fixed"
            print(f"{verb} {n} path(s) in {f.relative_to(ROOT).as_posix()}")

    for store in sorted((ROOT / "lab" / "agent-stores").glob("*")):
        for name, fn in (
            ("nca_train_registry.json", sanitize_registry),
            ("memory_manifest.json", sanitize_memory_manifest),
        ):
            f = store / name
            if f.is_file():
                _report(f, fn(f, write=write))

    for f in sorted((ROOT / "lab").rglob("ltm/pack.manifest.json")):
        store_id = f.parent.parent.name
        _report(f, sanitize_pack_manifest(f, store_id, write=write))
    if not total:
        print("OK: no absolute paths in store manifests.")
        return 0
    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
