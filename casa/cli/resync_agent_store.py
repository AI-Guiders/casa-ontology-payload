#!/usr/bin/env python3
"""Re-sync living agent store: zones migrate + honesty artifacts + MEMORY.md."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from casa.prisms.intelligence.migrate import migrate_intelligence_zones
from casa.prisms.memory.concept_layer import build_concept_honesty_report, write_concept_honesty_artifact
from casa.prisms.memory.forgetting import build_forget_honesty_report, write_forget_honesty_report
from casa.prisms.memory.memory_map import build_memory_map, write_memory_map_artifacts
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_mirror import copy_store_tree
from casa.prisms.shared.store_persist import save_runtime_state


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resync_agent_store(
    store_dir: Path,
    *,
    life_archive_dir: Path | None = None,
    message: str = "",
    skip_migrate: bool = False,
    mirror_archive: bool = False,
) -> dict:
    """Migrate zones, write honesty + memory map, optionally snapshot life-archive."""
    store_dir = store_dir.resolve()
    report: dict = {"store_dir": str(store_dir), "synced_at": _utc_now()}

    if not skip_migrate:
        mig = migrate_intelligence_zones(store_dir, persist=True)
        report["migration"] = {
            "intelligence_zones_version": mig.get("intelligence_zones_version"),
            "zones": mig.get("zones"),
        }
        try:
            from casa.prisms.intelligence.migrate_zone_prism_wire import migrate_zone_prism_wire

            wire = migrate_zone_prism_wire(store_dir, persist=True)
            report["zone_prism_wire"] = wire
        except ImportError:
            report["zone_prism_wire"] = {"skipped": True, "reason": "module_unavailable"}

    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])

    forget_honesty = build_forget_honesty_report(state, store_dir=store_dir)
    forget_path = write_forget_honesty_report(store_dir, forget_honesty)
    report["forget_honesty"] = {
        "path": str(forget_path),
        "gate_pass": forget_honesty.get("gate_pass"),
    }

    concept_honesty = build_concept_honesty_report(state)
    concept_path = write_concept_honesty_artifact(store_dir, concept_honesty)
    report["concept_honesty"] = {
        "path": str(concept_path),
        "gate_pass": concept_honesty.get("gate_pass"),
    }

    memory_map = build_memory_map(store_dir, state)
    map_paths = write_memory_map_artifacts(store_dir, memory_map)
    report["memory_map"] = map_paths

    save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)
    report["persist"] = {"saved": True}

    if mirror_archive and life_archive_dir is not None:
        archive_root = life_archive_dir.resolve()
        dst = archive_root / "store"
        stats = copy_store_tree(store_dir, dst, replace_dst=True)
        meta = {
            "synced_at": report["synced_at"],
            "source_store": str(store_dir),
            "message": message or "resync_agent_store",
            "migration": report.get("migration"),
            "stats": stats,
            "forget_honesty_gate_pass": forget_honesty.get("gate_pass"),
            "concept_honesty_gate_pass": concept_honesty.get("gate_pass"),
        }
        meta_path = archive_root / "sync_meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["life_archive"] = {"archive_dir": str(archive_root), "store": str(dst), "sync_meta": str(meta_path)}

    report["next"] = f"python -m casa.cli.chat --store {store_dir.name}"
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Re-sync agent store (migrate + honesty + MEMORY.md)")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument(
        "--life-archive-dir",
        type=Path,
        default=None,
        help="Optional von-neumann-life-archive clone root",
    )
    p.add_argument("--mirror-archive", action="store_true", help="Copy store/ into life-archive")
    p.add_argument("--message", default="", help="Snapshot note for sync_meta.json")
    p.add_argument("--skip-migrate", action="store_true")
    args = p.parse_args()

    store_dir = (args.store_dir or default_agent_store()).resolve()
    if not store_dir.is_dir():
        print(json.dumps({"error": f"store not found: {store_dir}"}, ensure_ascii=False), file=sys.stderr)
        return 1

    rep = resync_agent_store(
        store_dir,
        life_archive_dir=args.life_archive_dir,
        message=args.message,
        skip_migrate=args.skip_migrate,
        mirror_archive=args.mirror_archive,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
