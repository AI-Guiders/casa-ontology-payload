#!/usr/bin/env python3
"""Store checkpoint recovery — quarantine crash-zeroed JSON, boot from agent_field.db (ADR-0039)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.store_layout import field_state_path, ltm_root, runtime_checkpoint_paths

QUARANTINE_DIRNAME = ".crash-quarantine"
ZEROED_BYTE_RATIO = 0.95


def is_zeroed_file(path: Path, *, threshold: float = ZEROED_BYTE_RATIO) -> bool:
    if not path.is_file():
        return False
    raw = path.read_bytes()
    if not raw:
        return True
    return (raw.count(0) / len(raw)) >= threshold


def is_unreadable_json_file(path: Path) -> bool:
    """Crash-zeroed or invalid JSON — not merely missing."""
    if not path.is_file():
        return False
    if is_zeroed_file(path):
        return True
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return False
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return True


def quarantine_dir(store_dir: Path) -> Path:
    return store_dir.resolve() / QUARANTINE_DIRNAME


def quarantine_file(store_dir: Path, path: Path, *, tag: str = "zeroed") -> Path | None:
    path = path.resolve()
    if not path.is_file():
        return None
    dest_root = quarantine_dir(store_dir)
    dest_root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_root / f"{path.name}.{tag}.{ts}.bak"
    shutil.move(str(path), str(dest))
    return dest


def runtime_checkpoint_paths_list(store_dir: Path) -> list[Path]:
    store_dir = store_dir.resolve()
    ltm = ltm_root(store_dir)
    session = runtime_checkpoint_paths(store_dir)
    return [
        field_state_path(store_dir),
        session["agent_session"],
        ltm / "pack.manifest.json",
        ltm / "meta" / "router.json",
    ]


def minimal_ltm_pack_manifest(*, note: str = "") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "ltm_pack_manifest",
        "note": note or "minimal stub after checkpoint recovery; runtime from agent_field.db",
        "lattices": {},
        "control_lattices": {},
        "nca": {},
    }


def load_ltm_pack_manifest(ltm_dir: Path, *, store_dir: Path | None = None) -> dict[str, Any]:
    """Safe pack.manifest load — stub when missing or corrupt."""
    path = ltm_dir / "pack.manifest.json"
    if path.is_file() and not is_unreadable_json_file(path):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                return doc
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
    if store_dir is not None and path.is_file() and is_unreadable_json_file(path):
        quarantine_file(store_dir, path, tag="corrupt")
    stub = minimal_ltm_pack_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stub


def _persist_recovery_note(store_dir: Path, report: dict[str, Any]) -> None:
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    meta = read_session_meta(store_dir)
    meta["last_store_recovery_at"] = report.get("at")
    meta["last_store_recovery_ok"] = bool(report.get("recovered"))
    q = report.get("quarantined") or []
    if q:
        meta["last_store_recovery_quarantined"] = [str(x) for x in q]
    write_session_meta(store_dir, meta)


def recover_store_checkpoints(
    store_dir: Path,
    *,
    persist_thin: bool = False,
    quarantine_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Quarantine corrupt runtime JSON; optional thin overlay rebuild from agent_field.db."""
    from casa.domain.agent_field import field_db_stats, load_field_from_db

    store_dir = store_dir.resolve()
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats = field_db_stats(store_dir)
    targets = list(quarantine_paths or runtime_checkpoint_paths_list(store_dir))

    quarantined: list[str] = []
    for path in targets:
        if is_unreadable_json_file(path):
            dest = quarantine_file(store_dir, path)
            if dest is not None:
                quarantined.append(path.name)

    ltm = ltm_root(store_dir)
    pack_path = ltm / "pack.manifest.json"
    manifest_restored = False
    if not pack_path.is_file() or is_unreadable_json_file(pack_path):
        if pack_path.is_file():
            quarantine_file(store_dir, pack_path, tag="corrupt")
            quarantined.append(pack_path.name)
        load_ltm_pack_manifest(ltm, store_dir=store_dir)
        manifest_restored = True

    thin_rebuilt = False
    fs_path = field_state_path(store_dir)
    need_thin = persist_thin or (not fs_path.is_file() and stats.get("ok"))
    if need_thin and stats.get("ok"):
        db_state = load_field_from_db(store_dir)
        if db_state is not None:
            from casa.prisms.memory.memory_prisms import ensure_prisms
            from casa.prisms.shared.store_persist import save_runtime_state

            save_runtime_state(
                store_dir,
                ensure_prisms(db_state),
                force=True,
                thin=True,
                sync_ltm_on_save=False,
            )
            thin_rebuilt = True

    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "store_recovery",
        "at": at,
        "recovered": bool(quarantined or manifest_restored or thin_rebuilt),
        "quarantined": quarantined,
        "manifest_restored": manifest_restored,
        "thin_rebuilt": thin_rebuilt,
        "field_db": stats,
    }
    if report["recovered"]:
        _persist_recovery_note(store_dir, report)
    return report


def maybe_recover_store_on_wake(store_dir: Path) -> dict[str, Any]:
    """Prod hook: run before boot_store / agent_wake."""
    store_dir = store_dir.resolve()
    fs = field_state_path(store_dir)
    persist_thin = not fs.is_file() or is_unreadable_json_file(fs)
    return recover_store_checkpoints(store_dir, persist_thin=persist_thin)


def recovery_warnings_from_session(store_dir: Path) -> list[str]:
    from casa.prisms.control.fpn_state import read_session_meta

    meta = read_session_meta(store_dir)
    warnings: list[str] = []
    if meta.get("last_store_recovery_at"):
        warnings.append("checkpoint_recovered")
    q = meta.get("last_store_recovery_quarantined") or []
    if any("router" in str(x) for x in q):
        warnings.append("ltm_router_quarantined")
    if any("pack.manifest" in str(x) for x in q):
        warnings.append("ltm_pack_manifest_quarantined")
    return warnings
