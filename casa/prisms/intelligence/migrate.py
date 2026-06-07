#!/usr/bin/env python3
"""Migrate Intelligence Zones onto existing agent stores (ADR-0061)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.affect import core_affect_state, ensure_emotional_zone, spawn_emotional_zone
from casa.prisms.intelligence.character import spawn_character_zone
from casa.prisms.intelligence.executive import spawn_executive_zone
from casa.prisms.intelligence.logical import spawn_logical_zone
from casa.prisms.intelligence.social import spawn_social_zone
from casa.prisms.intelligence.spatial import spawn_spatial_zone
from casa.prisms.memory.agent_prism import agent_lattices, load_agent_prism, save_agent_prism
from casa.prisms.memory.bootstrap_agent_manifest import load_agent_bootstrap_manifest
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import save_runtime_state

INTELLIGENCE_ZONES_VERSION = 2


def migrate_emotional_zone(
    state: dict,
    manifest: dict[str, Any],
    *,
    tick: int = 0,
    force_respawn: bool = False,
) -> dict[str, Any]:
    cfg = _zone_cfg(manifest, "emotional_zone")
    if not cfg.get("enabled", True):
        return {"skipped": True, "reason": "disabled in manifest"}

    zone = ensure_emotional_zone(state)
    core = zone.get("core") or {}
    core_lid = str(cfg.get("core_lattice_id") or core.get("lattice_id") or "agent-limbic-core")
    sandbox_lid = str(cfg.get("sandbox_lattice_id") or "agent-affect-sandbox")
    lats = agent_lattices(state)

    needs_spawn = force_respawn or core_lid not in lats or sandbox_lid not in lats
    if needs_spawn:
        rep = spawn_emotional_zone(
            state,
            tick=tick,
            config={
                "core_lattice_id": core_lid,
                "sandbox_lattice_id": sandbox_lid,
                "concept_prefix_core": cfg.get("concept_prefix_core"),
                "concept_prefix_sandbox": cfg.get("concept_prefix_sandbox"),
                "initial_axes": cfg.get("initial_axes"),
                "zone_policy": cfg.get("zone_policy"),
            },
        )
        return {"spawned": True, **rep}

    return {
        "spawned": False,
        "core_lattice_id": core_lid,
        "sandbox_lattice_id": sandbox_lid,
        "core_axes": core_affect_state(state).axes.to_dict(),
    }


_SPAWNERS = {
    "emotional_zone": lambda state, cfg, tick: migrate_emotional_zone(
        state, {"agent_prisms": {**cfg}}, tick=tick
    ),
    "executive_zone": lambda state, cfg, tick: {
        "spawned": True,
        **spawn_executive_zone(state, config=cfg),
    },
    "social_zone": lambda state, cfg, tick: {
        "spawned": True,
        **spawn_social_zone(state, config=cfg),
    },
    "logical_zone": lambda state, cfg, tick: {
        "spawned": True,
        **spawn_logical_zone(state, config=cfg),
    },
    "character_zone": lambda state, cfg, tick: {
        "spawned": True,
        **spawn_character_zone(state, config=cfg),
    },
    "spatial_zone": lambda state, cfg, tick: spawn_spatial_zone(state, config=cfg),
}


def _zone_cfg(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    block = (manifest.get("agent_prisms") or {}).get(key) or {}
    return block if isinstance(block, dict) else {}


def migrate_all_zones(
    state: dict,
    manifest: dict[str, Any],
    *,
    tick: int = 0,
    persist: bool = False,
    store_dir: Path | None = None,
    force_respawn: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {"zones": {}, "intelligence_zones_version": INTELLIGENCE_ZONES_VERSION}
    wrapper = manifest if "agent_prisms" in manifest else {"agent_prisms": manifest}

    for key, spawner in _SPAWNERS.items():
        cfg = _zone_cfg(wrapper, key)
        if not cfg.get("enabled", key == "emotional_zone"):
            report["zones"][key.removesuffix("_zone")] = {"skipped": True}
            continue
        if key == "emotional_zone":
            rep = migrate_emotional_zone(
                state,
                wrapper,
                tick=tick,
                force_respawn=force_respawn,
            )
        else:
            rep = spawner(state, cfg, tick)
        report["zones"][key.removesuffix("_zone")] = rep

    meta = state.setdefault("meta", {})
    meta["intelligence_zones_version"] = INTELLIGENCE_ZONES_VERSION
    meta["intelligence_zones_migrated_at_tick"] = int(tick)

    if persist and store_dir is not None:
        save_agent_prism(store_dir, state)
        report["persist"] = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)

    report["field_version"] = int(state.get("field_version") or 0)
    return report


def migrate_intelligence_zones(
    store_dir: Path,
    *,
    manifest_path: Path | None = None,
    tick: int = 0,
    persist: bool = True,
    force_respawn: bool = False,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    manifest = load_agent_bootstrap_manifest(manifest_path)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name
    load_agent_prism(store_dir, state)

    report = migrate_all_zones(
        state,
        manifest,
        tick=tick,
        persist=False,
        force_respawn=force_respawn,
    )
    report["store"] = store_dir.name

    if persist:
        save_agent_prism(store_dir, state)
        report["persist"] = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)

    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Migrate Intelligence Zones (ADR-0061)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--tick", type=int, default=0)
    p.add_argument("--force-respawn", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.dry_run:
        manifest = load_agent_bootstrap_manifest(args.manifest)
        enabled = [k for k in _SPAWNERS if _zone_cfg(manifest, k).get("enabled", k == "emotional_zone")]
        print(json.dumps({"dry_run": True, "enabled_zones": enabled}, indent=2))
        return 0

    rep = migrate_intelligence_zones(
        args.store_dir,
        manifest_path=args.manifest,
        tick=args.tick,
        persist=True,
        force_respawn=args.force_respawn,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
