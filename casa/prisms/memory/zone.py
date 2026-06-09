#!/usr/bin/env python3
"""Memory Zone — explicit / implicit / immutable catalog (ADR-0068)."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_wire import prism_hippo, prism_memory
from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.memory_prisms import memory_lattices

CORE_LATTICE = "agent-memory-core"
SANDBOX_LATTICE = "agent-memory-sandbox"
CORE_PREFIX = "agent.memory."
SANDBOX_PREFIX = "agent.memory.lab."


def _default_explicit(cfg: dict[str, Any]) -> dict[str, Any]:
    explicit_cfg = cfg.get("explicit") if isinstance(cfg.get("explicit"), dict) else {}
    episodic_cfg = explicit_cfg.get("episodic") if isinstance(explicit_cfg.get("episodic"), dict) else {}
    semantic_cfg = explicit_cfg.get("semantic") if isinstance(explicit_cfg.get("semantic"), dict) else {}
    return {
        "episodic": {
            "hippo_prism_ref": str(episodic_cfg.get("hippo_prism") or "prism_hippo"),
            "hippo_lattice_ids": [],
            "dialogue_ring_ref": "dialogue" if episodic_cfg.get("dialogue", True) else "",
            "journal_domains": list(episodic_cfg.get("journal_domains") or []),
        },
        "semantic": {
            "ltm_prism_ref": str(semantic_cfg.get("ltm_prism") or "prism_memory"),
            "wm_prism_ref": str(semantic_cfg.get("wm_prism") or "wm_prism"),
            "ltm_lattice_ids": [],
            "active_shards": dict(semantic_cfg.get("active_shards") or {}),
        },
    }


def _default_implicit(cfg: dict[str, Any]) -> dict[str, Any]:
    implicit_cfg = cfg.get("implicit") if isinstance(cfg.get("implicit"), dict) else {}
    procedural_cfg = implicit_cfg.get("procedural") if isinstance(implicit_cfg.get("procedural"), dict) else {}
    priming_cfg = implicit_cfg.get("priming") if isinstance(implicit_cfg.get("priming"), dict) else {}
    return {
        "procedural": {
            "intent_prism_ref": str(procedural_cfg.get("intent_prism") or "intent_prism"),
            "nca_registry_ref": "nca_registry" if procedural_cfg.get("nca_registry", True) else "",
        },
        "priming": {
            "bind_decay_halflife_ticks": int(priming_cfg.get("decay_halflife_ticks") or 6),
            "last_activation_tick": int(priming_cfg.get("last_activation_tick") or -1),
        },
    }


def _default_immutable(cfg: dict[str, Any]) -> dict[str, Any]:
    imm_cfg = cfg.get("immutable") if isinstance(cfg.get("immutable"), dict) else {}
    mut_cfg = cfg.get("mutability") if isinstance(cfg.get("mutability"), dict) else {}
    patterns = list(imm_cfg.get("lattice_patterns") or mut_cfg.get("immutable_lattice_patterns") or [])
    if not patterns:
        patterns = ["alphabet-*", "syllables-ru", "morph-role-*"]
    return {
        "lattice_ids": list(imm_cfg.get("lattice_ids") or []),
        "lattice_patterns": patterns,
        "write_gate_ref": str(imm_cfg.get("write_gate") or mut_cfg.get("write_gate") or "genetic.promote_canon"),
        "domains": dict(imm_cfg.get("domains") or {"lang": {}, "math": {}, "concept": {}, "vis": {}}),
        "theories": list(imm_cfg.get("theories") or []),
    }


def ensure_memory_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wire Memory Zone under intelligence_zones.memory (ADR-0068 §5)."""
    cfg = config or {}
    ensure_agent_prism(state)
    root = intelligence_root(state)
    zone = root.setdefault("memory", {})
    zone.setdefault("adr", str(cfg.get("adr") or "0068"))
    zone.setdefault("explicit", _default_explicit(cfg))
    zone.setdefault("implicit", _default_implicit(cfg))
    zone.setdefault("immutable", _default_immutable(cfg))
    zone.setdefault(
        "consolidate",
        {
            "last_sleep_at_tick": int((zone.get("consolidate") or {}).get("last_sleep_at_tick") or -1),
            "replay_queue_depth": int((zone.get("consolidate") or {}).get("replay_queue_depth") or 0),
            "merge_policy_ref": str((zone.get("consolidate") or {}).get("merge_policy_ref") or "run_sleep"),
        },
    )
    zone.setdefault("core_lattice_id", str(cfg.get("core_lattice_id") or CORE_LATTICE))
    zone.setdefault("sandbox_lattice_id", str(cfg.get("sandbox_lattice_id") or SANDBOX_LATTICE))
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    return zone


def _index_ltm_lattices(state: dict, zone: dict[str, Any]) -> list[str]:
    mem = memory_lattices(state)
    zone["explicit"]["semantic"]["ltm_lattice_ids"] = sorted(mem.keys())
    return zone["explicit"]["semantic"]["ltm_lattice_ids"]


def _index_hippo_lattices(state: dict, zone: dict[str, Any]) -> list[str]:
    hip = prism_hippo(state).get("lattices") or {}
    zone["explicit"]["episodic"]["hippo_lattice_ids"] = sorted(hip.keys())
    return zone["explicit"]["episodic"]["hippo_lattice_ids"]


def spawn_memory_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Catalog lattices + prism refs for Memory Zone."""
    cfg = config or {}
    zone = ensure_memory_zone(state, config=cfg)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    ltm_ids = _index_ltm_lattices(state, zone)
    hippo_ids = _index_hippo_lattices(state, zone)
    active = str(prism_memory(state).get("active_lattice") or "")
    from casa.prisms.memory.write_gate import sync_immutable_catalog

    imm_rep = sync_immutable_catalog(state)
    return {
        **rep,
        "ltm_lattice_count": len(ltm_ids),
        "hippo_lattice_count": len(hippo_ids),
        "active_lattice": active,
        "immutable_catalog": imm_rep,
    }


def memory_zone_snapshot(state: dict) -> dict[str, Any]:
    zone = ensure_memory_zone(state)
    return {
        "core_lattice_id": zone.get("core_lattice_id"),
        "sandbox_lattice_id": zone.get("sandbox_lattice_id"),
        "ltm_lattice_ids": list((zone.get("explicit") or {}).get("semantic", {}).get("ltm_lattice_ids") or []),
        "hippo_lattice_ids": list((zone.get("explicit") or {}).get("episodic", {}).get("hippo_lattice_ids") or []),
        "immutable_patterns": list((zone.get("immutable") or {}).get("lattice_patterns") or []),
    }


def memory_kind_for_lattice(state: dict, lattice_id: str) -> dict[str, Any]:
    """Tag lookup from meta.zone_lattice_index (P11)."""
    idx = (state.get("meta") or {}).get("zone_lattice_index") or {}
    row = idx.get(str(lattice_id))
    return dict(row) if isinstance(row, dict) else {}


def lattice_zone_tag(state: dict, lattice_id: str) -> dict[str, Any]:
    """Index tag or zone-prism-map classification fallback."""
    tag = memory_kind_for_lattice(state, lattice_id)
    if tag:
        return tag
    from casa.prisms.intelligence.zone_prism_map import classify_lattice_id, load_zone_prism_map

    return classify_lattice_id(str(lattice_id), load_zone_prism_map()).to_dict()
