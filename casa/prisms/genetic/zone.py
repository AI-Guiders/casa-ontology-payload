#!/usr/bin/env python3
"""Genetic Zone — species genome seal + immutable constants (ADR-0062)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.shared.store_layout import agent_prism_root

DEFAULT_GENOME: dict[str, Any] = {
    "schema_version": 1,
    "kind": "agent_genome",
    "species_id": "casa.von-neumann.ru-v1",
    "zone_proportions": {
        "executive": 1.0,
        "emotional": 0.85,
        "social": 0.9,
        "logical": 0.95,
        "linguistic": 1.0,
        "spatial": 0.5,
        "character": 0.6,
        "perceptual": 0.8,
        "metabolic": 1.0,
    },
    "ema_limits": {
        "character_alpha_max": 0.08,
        "character_alpha_default": 0.05,
    },
    "signal_decay": {
        "wm_theta_decay_floor": 0.12,
        "intent_theta_decay_floor": 0.08,
        "wm_theta_decay": 0.2,
        "intent_theta_decay": 0.12,
    },
    "forgetting_genotype": {
        "implicit": {
            "priming_alpha_retain": 0.2,
        },
        "episodic": {
            "beta_fade": 0.08,
            "fade_every_n_ticks": 8,
            "salience_floor": 0.05,
            "hippo_cap": 240,
            "dialogue_ring_cap": 256,
        },
        "nca": {
            "erosion_epsilon": 0.02,
        },
        "canon_susceptibility": 0.0,
    },
    "surprise_gains": {
        "metabolic_fatigue": 0.12,
        "affect_arousal": 0.15,
        "dan_boost_cap": 24,
    },
    "metabolic": {
        "policy": {
            "atp_per_tick_base": 0.02,
            "cost_surprise": 0.08,
            "cost_compose_token": 0.008,
            "sleep_threshold": 0.85,
            "recovery_per_idle_tick": 0.06,
        }
    },
    "promote_canon": {
        "sandbox_theta": 0.65,
        "bundle_tier_gate": "RU-ε",
        "algorithm": "agent_promote_canon_lattice_v1",
    },
    "allowed_zone_ids": [
        "emotional",
        "executive",
        "social",
        "logical",
        "character",
        "spatial",
        "perceptual",
        "metabolic",
        "linguistic",
    ],
}


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def genome_hash(spec: dict[str, Any]) -> str:
    payload = {k: v for k, v in spec.items() if k != "genome_hash"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def build_genome_spec(manifest_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = copy.deepcopy(DEFAULT_GENOME)
    cfg = manifest_cfg or {}
    if cfg.get("species_id"):
        spec["species_id"] = str(cfg["species_id"])
    for key in (
        "zone_proportions",
        "ema_limits",
        "signal_decay",
        "surprise_gains",
        "promote_canon",
        "metabolic",
        "forgetting_genotype",
    ):
        if isinstance(cfg.get(key), dict):
            spec[key] = {**spec.get(key, {}), **cfg[key]}
    if isinstance(cfg.get("forgetting_genotype"), dict):
        fg = cfg["forgetting_genotype"]
        if isinstance(fg.get("implicit"), dict):
            spec.setdefault("forgetting_genotype", {}).setdefault("implicit", {}).update(fg["implicit"])
        if isinstance(fg.get("episodic"), dict):
            spec.setdefault("forgetting_genotype", {}).setdefault("episodic", {}).update(fg["episodic"])
        if isinstance(fg.get("nca"), dict):
            spec.setdefault("forgetting_genotype", {}).setdefault("nca", {}).update(fg["nca"])
    if isinstance(cfg.get("policy"), dict):
        spec.setdefault("metabolic", {})["policy"] = {
            **spec.get("metabolic", {}).get("policy", {}),
            **cfg["policy"],
        }
    spec["genome_hash"] = genome_hash(spec)
    return spec


def ensure_genetic_zone(state: dict) -> dict[str, Any]:
    block = ensure_agent_prism(state)
    zone = block.setdefault("genetic_zone", {})
    zone.setdefault("immutable", False)
    zone.setdefault("species_id", DEFAULT_GENOME["species_id"])
    zone.setdefault("genome_hash", "")
    zone.setdefault("sealed_at_tick", -1)
    zone.setdefault("spec", {})
    return zone


def genetic_zone_block(state: dict) -> dict[str, Any]:
    return ensure_genetic_zone(state)


def load_genetic_zone(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    zone = ensure_genetic_zone(state)
    path = agent_prism_root(store_dir) / str(zone.get("genome_file") or "genome.v1.json")
    if not path.is_file():
        path = agent_prism_root(store_dir) / "genome.v1.json"
    if path.is_file():
        spec = json.loads(path.read_text(encoding="utf-8"))
        zone["spec"] = spec
        zone["species_id"] = str(spec.get("species_id") or zone["species_id"])
        zone["genome_hash"] = str(spec.get("genome_hash") or genome_hash(spec))
        zone["immutable"] = True
        return {"loaded": True, "path": str(path), "genome_hash": zone["genome_hash"]}
    return {"loaded": False, "path": str(path)}


def seal_genetic_zone(
    store_dir: Path,
    state: dict,
    manifest_cfg: dict[str, Any] | None = None,
    *,
    tick: int = 0,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    zone = ensure_genetic_zone(state)
    if zone.get("immutable") and zone.get("genome_hash"):
        return {"sealed": False, "reason": "already_sealed", "genome_hash": zone["genome_hash"]}
    spec = build_genome_spec(manifest_cfg)
    root = agent_prism_root(store_dir)
    root.mkdir(parents=True, exist_ok=True)
    genome_file = str((manifest_cfg or {}).get("genome_file") or "genome.v1.json")
    path = root / genome_file
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zone.update(
        {
            "immutable": True,
            "species_id": spec["species_id"],
            "genome_hash": spec["genome_hash"],
            "sealed_at_tick": int(tick),
            "genome_file": genome_file,
            "spec": spec,
        }
    )
    rep: dict[str, Any] = {"sealed": True, "genome_hash": spec["genome_hash"], "path": str(path)}
    try:
        from casa.prisms.genetic.passport import write_genome_passport_artifact

        rep["genome_passport"] = write_genome_passport_artifact(store_dir, state)
    except ImportError:
        pass
    return rep


def _walk_get(obj: Any, parts: list[str]) -> Any:
    cur = obj
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def genetic_constant(state: dict, path: str, default: Any = None) -> Any:
    zone = ensure_genetic_zone(state)
    spec = zone.get("spec") or {}
    val = _walk_get(spec, path.split(".")) if spec else None
    if val is None:
        val = _walk_get(DEFAULT_GENOME, path.split("."))
    return default if val is None else val


def verify_genome_hash(state: dict) -> bool:
    zone = ensure_genetic_zone(state)
    spec = zone.get("spec")
    if not isinstance(spec, dict) or not spec:
        return False
    expected = str(zone.get("genome_hash") or "")
    return expected == genome_hash(spec)


def species_passport(state: dict) -> dict[str, Any]:
    zone = ensure_genetic_zone(state)
    return {
        "species_id": zone.get("species_id"),
        "genome_hash": zone.get("genome_hash"),
        "immutable": bool(zone.get("immutable")),
        "sealed_at_tick": zone.get("sealed_at_tick"),
        "valid": verify_genome_hash(state),
    }
