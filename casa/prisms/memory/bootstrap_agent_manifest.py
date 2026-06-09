#!/usr/bin/env python3
"""Declarative agent bootstrap from design/agent-bootstrap-manifest.v1.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import append_journal_entry, journal_stats
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.agent_prism import create_agent_lattice, ensure_agent_prism, load_agent_prism, save_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_persist import save_runtime_state

MANIFEST_VERSION = 1
DEFAULT_MANIFEST = Path(__file__).resolve().parents[3] / "design" / "agent-bootstrap-manifest.v1.json"


def default_manifest_path() -> Path:
    return DEFAULT_MANIFEST


def load_agent_bootstrap_manifest(path: Path | None = None) -> dict[str, Any]:
    mp = (path or default_manifest_path()).resolve()
    if not mp.is_file():
        raise FileNotFoundError(f"agent bootstrap manifest not found: {mp}")
    data = json.loads(mp.read_text(encoding="utf-8"))
    if int(data.get("schema_version") or 0) != MANIFEST_VERSION:
        raise ValueError(f"unsupported manifest schema: {data.get('schema_version')!r}")
    return data


def _format_obj(obj: Any, *, display_name: str, notebook: str = "") -> Any:
    if isinstance(obj, str):
        return obj.format(display_name=display_name, notebook=notebook)
    if isinstance(obj, list):
        return [_format_obj(x, display_name=display_name, notebook=notebook) for x in obj]
    if isinstance(obj, dict):
        return {k: _format_obj(v, display_name=display_name, notebook=notebook) for k, v in obj.items()}
    return obj


def _bootstrap_self_tier(
    store_dir: Path,
    state: dict,
    manifest: dict[str, Any],
    *,
    display_name: str,
) -> list[str]:
    cfg = manifest.get("self_tier") or {}
    lat = cfg.get("default_lattice") or {}
    lid = str(lat.get("lattice_id") or "agent-self-default")
    create_agent_lattice(
        state,
        lid,
        width=int(lat.get("width") or 32),
        height=int(lat.get("height") or 32),
        concept_prefix=str(lat.get("concept_prefix") or "agent.self."),
    )

    journal_rows: list[str] = []
    notebooks = [str(n) for n in (cfg.get("notebooks") or ["self"])]
    for spec in cfg.get("journal_entries") or []:
        if not isinstance(spec, dict):
            continue
        if spec.get("domain_from_notebook"):
            for nb in notebooks:
                if nb == "self":
                    continue
                row = _format_obj(spec, display_name=display_name, notebook=nb)
                domain = nb.replace("_", "-")
                append_journal_entry(
                    store_dir,
                    {
                        "kind": str(row.get("kind") or "note"),
                        "text": str(row.get("text_template") or row.get("text") or ""),
                        "tags": list(row.get("tags") or []),
                        "meta": dict(row.get("meta") or {}),
                    },
                    domain=domain,
                )
                journal_rows.append(f"{nb}/bootstrap")
            continue
        row = _format_obj(spec, display_name=display_name)
        append_journal_entry(
            store_dir,
            {
                "kind": str(row.get("kind") or "note"),
                "text": str(row.get("text_template") or row.get("text") or ""),
                "tags": list(row.get("tags") or []),
                "meta": dict(row.get("meta") or {}),
            },
            domain=str(row.get("domain") or "self"),
        )
        journal_rows.append(f"{row.get('domain', 'self')}/bootstrap")

    remember = cfg.get("remember_on_boot")
    if isinstance(remember, dict):
        agent_remember(
            store_dir,
            state,
            _format_obj(remember, display_name=display_name),
            scope="self",
            persist=False,
        )
    return journal_rows


def _bootstrap_agent_prisms(
    state: dict,
    manifest: dict[str, Any],
    *,
    tick: int = 0,
    store_dir: Path | None = None,
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    prisms = manifest.get("agent_prisms") or {}

    genetic_cfg = prisms.get("genetic_zone") or {}
    if genetic_cfg.get("enabled") and store_dir is not None:
        from casa.prisms.genetic import load_genetic_zone, seal_genetic_zone
        from casa.prisms.genetic.zone import ensure_genetic_zone

        load_genetic_zone(store_dir, state)
        zone = ensure_genetic_zone(state)
        if zone.get("immutable") and zone.get("genome_hash"):
            applied.append(
                {
                    "prism": "genetic_zone",
                    "adr": genetic_cfg.get("adr") or "0062",
                    "loaded": True,
                    "genome_hash": zone.get("genome_hash"),
                }
            )
        else:
            rep = seal_genetic_zone(store_dir, state, genetic_cfg, tick=tick)
            applied.append({"prism": "genetic_zone", "adr": genetic_cfg.get("adr") or "0062", **rep})

    wm = prisms.get("wm_prism") or {}
    if wm.get("enabled"):
        from casa.prisms.memory.wm import DEFAULT_SCRATCH_LATTICE, spawn_wm_lattice

        block = ensure_agent_prism(state)
        policy = wm.get("wm_policy")
        if isinstance(policy, dict):
            block["wm_policy"] = dict(policy)
        if wm.get("spawn_on_bootstrap", True):
            lid = spawn_wm_lattice(state, tick=tick, topic_slug="scratch", overloaded=False)
            applied.append(
                {
                    "prism": "wm_prism",
                    "adr": wm.get("adr"),
                    "lattice_id": lid or DEFAULT_SCRATCH_LATTICE,
                    "wm_policy": block.get("wm_policy"),
                }
            )

    intent_cfg = prisms.get("intent_prism") or {}
    if intent_cfg.get("enabled"):
        from casa.prisms.memory.intent import DEFAULT_INTENT_LATTICE, spawn_intent_lattice

        block = ensure_agent_prism(state)
        ipolicy = intent_cfg.get("intent_policy")
        if isinstance(ipolicy, dict):
            block["intent_policy"] = dict(ipolicy)
        if intent_cfg.get("spawn_on_bootstrap", True):
            lid = spawn_intent_lattice(state, tick=tick)
            applied.append(
                {
                    "prism": "intent_prism",
                    "adr": intent_cfg.get("adr"),
                    "lattice_id": lid or DEFAULT_INTENT_LATTICE,
                    "intent_policy": block.get("intent_policy"),
                }
            )

    zone_spawners: list[tuple[str, str, str, str]] = [
        ("emotional_zone", "0060", "spawn_emotional_zone", "casa.prisms.affect"),
        ("executive_zone", "0061", "spawn_executive_zone", "casa.prisms.intelligence"),
        ("social_zone", "0061", "spawn_social_zone", "casa.prisms.intelligence"),
        ("logical_zone", "0061", "spawn_logical_zone", "casa.prisms.intelligence"),
        ("character_zone", "0061", "spawn_character_zone", "casa.prisms.intelligence"),
        ("spatial_zone", "0061", "spawn_spatial_zone", "casa.prisms.intelligence"),
        ("metabolic_zone", "0064", "spawn_metabolic_zone", "casa.prisms.metabolic"),
        ("perceptual_zone", "0063", "spawn_perceptual_zone", "casa.prisms.perceptual"),
        ("linguistic_zone", "0061", "spawn_linguistic_zone", "casa.prisms.intelligence"),
        ("memory_zone", "0068", "spawn_memory_zone", "casa.prisms.memory.zone"),
    ]
    for key, adr, fn_name, mod_path in zone_spawners:
        cfg = prisms.get(key) or {}
        if not cfg.get("enabled"):
            continue
        if not cfg.get("spawn_on_bootstrap", True):
            continue
        mod = __import__(mod_path, fromlist=[fn_name])
        spawner = getattr(mod, fn_name)
        spawn_kwargs: dict[str, Any] = {
            "core_lattice_id": cfg.get("core_lattice_id"),
            "concept_prefix_core": cfg.get("concept_prefix_core"),
        }
        if key != "character_zone":
            spawn_kwargs["sandbox_lattice_id"] = cfg.get("sandbox_lattice_id")
            spawn_kwargs["concept_prefix_sandbox"] = cfg.get("concept_prefix_sandbox")
        if key == "emotional_zone":
            spawn_kwargs["initial_axes"] = cfg.get("initial_axes")
            spawn_kwargs["zone_policy"] = cfg.get("zone_policy")
            rep = spawner(state, tick=tick, config=spawn_kwargs)
        elif key == "spatial_zone":
            spawn_kwargs["enabled"] = cfg.get("enabled", False)
            rep = spawner(state, config=spawn_kwargs)
            if not rep.get("spawned", True):
                continue
        else:
            if key == "social_zone" and cfg.get("initial_trust") is not None:
                spawn_kwargs["initial_trust"] = cfg.get("initial_trust")
            if key == "logical_zone" and cfg.get("initial_math_confidence") is not None:
                spawn_kwargs["initial_math_confidence"] = cfg.get("initial_math_confidence")
            if key == "linguistic_zone" and cfg.get("initial_discourse_confidence") is not None:
                spawn_kwargs["initial_discourse_confidence"] = cfg.get("initial_discourse_confidence")
            if key == "memory_zone":
                for sub in ("explicit", "implicit", "immutable", "mutability"):
                    if isinstance(cfg.get(sub), dict):
                        spawn_kwargs[sub] = cfg.get(sub)
            if key == "metabolic_zone":
                if cfg.get("initial_atp") is not None:
                    spawn_kwargs["initial_atp"] = cfg.get("initial_atp")
                if isinstance(cfg.get("policy"), dict):
                    spawn_kwargs["policy"] = cfg.get("policy")
            if key == "perceptual_zone":
                if cfg.get("active_modalities"):
                    spawn_kwargs["active_modalities"] = cfg.get("active_modalities")
                if isinstance(cfg.get("fan_out"), dict):
                    spawn_kwargs["fan_out"] = cfg.get("fan_out")
            if key == "character_zone":
                if cfg.get("initial_openness") is not None:
                    spawn_kwargs["initial_openness"] = cfg.get("initial_openness")
                if cfg.get("initial_directness") is not None:
                    spawn_kwargs["initial_directness"] = cfg.get("initial_directness")
            if cfg.get("zone_policy"):
                spawn_kwargs["zone_policy"] = cfg.get("zone_policy")
            rep = spawner(state, config=spawn_kwargs)
        applied.append({"prism": key, "adr": cfg.get("adr") or adr, **rep})

    return applied


def bootstrap_agent_from_manifest(
    store_dir: Path,
    state: dict,
    manifest: dict[str, Any] | None = None,
    *,
    display_name: str = "Нейманн",
    tick: int = 0,
) -> dict[str, Any]:
    """Apply manifest to store+state (Self tier lattices, journal, agent prisms)."""
    store_dir = store_dir.resolve()
    manifest = manifest or load_agent_bootstrap_manifest()
    ensure_prisms(state)
    load_agent_prism(store_dir, state)

    journal_rows = _bootstrap_self_tier(store_dir, state, manifest, display_name=display_name)
    prism_rows = _bootstrap_agent_prisms(state, manifest, tick=tick, store_dir=store_dir)

    save_agent_prism(store_dir, state)
    return {
        "manifest": str(default_manifest_path()),
        "manifest_kind": manifest.get("kind"),
        "journal_bootstrapped": journal_rows,
        "agent_prisms": prism_rows,
    }


def apply_agent_bootstrap(
    store_dir: Path,
    *,
    display_name: str = "Нейманн",
    locale: str = "ru",
    manifest_path: Path | None = None,
    seed_host_canon: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    """Full cold-path: manifest + optional host canon."""
    from casa.prisms.memory.bootstrap_host_canon import bootstrap_host_canon_lattices
    from casa.prisms.shared.store_boot import boot_store

    store_dir = store_dir.resolve()
    manifest = load_agent_bootstrap_manifest(manifest_path)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name

    rep = bootstrap_agent_from_manifest(
        store_dir,
        state,
        manifest,
        display_name=display_name,
    )
    host_cfg = manifest.get("host_canon") or {}
    if seed_host_canon and host_cfg.get("morph_role_by_locale", True):
        rep["host_canon"] = bootstrap_host_canon_lattices(
            store_dir,
            state,
            locale=locale,
            persist=False,
        )
    if persist:
        rep["persist"] = save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)
    rep["journal"] = journal_stats(store_dir)
    return rep


def main() -> None:
    p = argparse.ArgumentParser(description="Apply agent bootstrap manifest")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--display-name", default="Нейманн")
    p.add_argument("--locale", default="ru")
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--no-host-canon", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("show-default", help="Print default manifest path and summary")
    args = p.parse_args()

    if args.cmd == "show-default":
        manifest = load_agent_bootstrap_manifest(args.manifest)
        print(
            json.dumps(
                {
                    "path": str((args.manifest or default_manifest_path()).resolve()),
                    "prisms": list((manifest.get("agent_prisms") or {}).keys()),
                    "notebooks": (manifest.get("self_tier") or {}).get("notebooks"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.dry_run:
        manifest = load_agent_bootstrap_manifest(args.manifest)
        print(json.dumps({"would_apply": manifest.get("kind"), "store": str(args.store_dir)}, ensure_ascii=False, indent=2))
        return

    rep = apply_agent_bootstrap(
        args.store_dir,
        display_name=args.display_name,
        locale=args.locale,
        manifest_path=args.manifest,
        seed_host_canon=not args.no_host_canon,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
