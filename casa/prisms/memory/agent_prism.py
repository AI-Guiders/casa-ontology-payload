#!/usr/bin/env python3
"""Agent-owned memory prism — lattices + NCA outside profile ltm/ export."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.prism_wire import normalize_prisms, prism_agent
from casa.prisms.shared.store_layout import (
    agent_bridges_path,
    agent_lattice_path,
    agent_lattices_dir,
    agent_manifest_path,
    agent_prism_root,
    rel_to_repo,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.nca_codec import tokens_from_lattice
from casa.prisms.memory.stack import _place_token, decode_lattice
from casa.prisms.shared.codec_grid import Grid

AGENT_MANIFEST_VERSION = 1
_LATTICE_ID_RE = re.compile(r"^agent-[a-z0-9_-]{1,48}$")


def safe_agent_lattice_id(lattice_id: str) -> str:
    lid = str(lattice_id or "").strip()
    if not _LATTICE_ID_RE.fullmatch(lid):
        raise ValueError(f"agent lattice id must match agent-{{slug}}: {lattice_id!r}")
    return lid


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def agent_lattices(state: dict) -> dict[str, dict]:
    normalize_prisms(state)
    return prism_agent(state).setdefault("lattices", {})


def ensure_agent_prism(state: dict) -> dict:
    ensure_prisms(state)
    block = prism_agent(state)
    block.setdefault("subsystem", "agent_owned")
    block.setdefault("lattices", {})
    block.setdefault("nca", {"models": {}})
    block["nca"].setdefault("models", {})
    return block


def empty_agent_lattice(*, width: int = 32, height: int = 32, z_level: int = 0, concept_prefix: str = "agent.") -> dict:
    n = width * height
    return {
        "z_level": z_level,
        "width": width,
        "height": height,
        "cells": [[] for _ in range(n)],
        "concept_prefix": concept_prefix,
        "owner": "agent",
    }


def create_agent_lattice(
    state: dict,
    lattice_id: str,
    *,
    width: int = 32,
    height: int = 32,
    z_level: int = 0,
    concept_prefix: str = "agent.",
) -> dict[str, Any]:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid in lats:
        raise ValueError(f"agent lattice already exists: {lid}")
    lat = empty_agent_lattice(width=width, height=height, z_level=z_level, concept_prefix=concept_prefix)
    lats[lid] = lat
    block = ensure_agent_prism(state)
    if not block.get("active_lattice"):
        block["active_lattice"] = lid
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {"lattice_id": lid, "width": width, "height": height, "z_level": z_level}


def delete_agent_lattice(state: dict, lattice_id: str) -> bool:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid not in lats:
        return False
    del lats[lid]
    block = prism_agent(state)
    models = block.setdefault("nca", {}).setdefault("models", {})
    models.pop(lid, None)
    if block.get("active_lattice") == lid:
        block["active_lattice"] = next(iter(lats), None)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return True


def place_agent_token(
    state: dict,
    lattice_id: str,
    token: str,
    *,
    x: int | None = None,
    y: int | None = None,
    copies: int = 1,
    radius: int = 4,
) -> dict[str, Any]:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid not in lats:
        raise KeyError(f"unknown agent lattice: {lid}")
    tok = str(token or "").strip()
    if not tok:
        raise ValueError("token is required")

    lat = lats[lid]
    w, h = int(lat["width"]), int(lat["height"])
    g = Grid(width=w, height=h, cells=[list(c) for c in lat["cells"]])

    if x is not None and y is not None:
        xi, yi = int(x), int(y)
        if not (0 <= xi < w and 0 <= yi < h):
            raise ValueError(f"coordinates out of bounds: ({xi},{yi}) for {w}x{h}")
        idx = g.index(xi, yi)
        if tok not in g.cells[idx]:
            g.cells[idx].append(tok)
        mode = "exact"
    else:
        g = _place_token(g, tok, tok, copies=max(1, copies), radius=radius)
        mode = "cluster"

    lat["cells"] = g.cells
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {"lattice_id": lid, "token": tok, "mode": mode, "token_count": len(tokens_from_lattice(lat))}


def read_agent_lattice(state: dict, lattice_id: str, *, min_votes: int = 1) -> dict[str, Any]:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid not in lats:
        raise KeyError(f"unknown agent lattice: {lid}")
    lat = lats[lid]
    dec = decode_lattice(lat, min_votes=min_votes)
    return {
        "lattice_id": lid,
        "width": lat.get("width"),
        "height": lat.get("height"),
        "token_count": len(tokens_from_lattice(lat)),
        "decode": dec,
    }


def list_agent_lattices(state: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    block = prism_agent(state)
    models = (block.get("nca") or {}).get("models") or {}
    for lid, lat in sorted(agent_lattices(state).items()):
        rows.append(
            {
                "lattice_id": lid,
                "width": lat.get("width"),
                "height": lat.get("height"),
                "z_level": lat.get("z_level"),
                "token_count": len(tokens_from_lattice(lat)),
                "nca_model": models.get(lid),
                "active": block.get("active_lattice") == lid,
            }
        )
    return rows


def _load_manifest(store_dir: Path) -> dict[str, Any]:
    path = agent_manifest_path(store_dir)
    if not path.is_file():
        return {"schema_version": AGENT_MANIFEST_VERSION, "lattices": {}, "nca": {"models": {}}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("schema_version", AGENT_MANIFEST_VERSION)
    data.setdefault("lattices", {})
    data.setdefault("nca", {"models": {}})
    data["nca"].setdefault("models", {})
    return data


def _agent_zone_state(block: dict[str, Any]) -> dict[str, Any]:
    """Self-tier overlay: Intelligence Zones + prism policies (survives thin checkpoint)."""
    out: dict[str, Any] = {}
    for key in ("genetic_zone", "intelligence_zones", "wm_policy", "intent_policy"):
        if key in block and block[key] is not None:
            out[key] = copy.deepcopy(block[key])
    return out


def _apply_agent_zone_state(block: dict[str, Any], raw: dict[str, Any] | None) -> None:
    if not isinstance(raw, dict):
        return
    for key in ("genetic_zone", "emotional_zone", "intelligence_zones", "wm_policy", "intent_policy"):
        if key in raw and raw[key] is not None:
            if key == "emotional_zone":
                block.setdefault("emotional_zone", copy.deepcopy(raw[key]))
            else:
                block[key] = copy.deepcopy(raw[key])


def save_agent_prism(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    ensure_agent_prism(state)
    from casa.prisms.affect.zone import consolidate_emotional_zone_wire

    consolidate_emotional_zone_wire(state)
    root = agent_prism_root(store_dir)
    ldir = agent_lattices_dir(store_dir)
    ldir.mkdir(parents=True, exist_ok=True)

    lats = agent_lattices(state)
    manifest_lattices: dict[str, Any] = {}
    for lid, lat in lats.items():
        path = agent_lattice_path(store_dir, lid)
        path.write_text(json.dumps(lat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest_lattices[lid] = {
            "path": path.relative_to(root).as_posix(),
            "width": lat.get("width"),
            "height": lat.get("height"),
            "token_count": len(tokens_from_lattice(lat)),
            "updated_at": _utc_now(),
        }

    block = prism_agent(state)
    nca_models = dict((block.get("nca") or {}).get("models") or {})
    bridges_rel = None
    if agent_bridges_path(store_dir).is_file():
        bridges_rel = agent_bridges_path(store_dir).relative_to(root).as_posix()

    manifest = {
        "schema_version": AGENT_MANIFEST_VERSION,
        "kind": "agent_prism",
        "updated_at": _utc_now(),
        "active_lattice": block.get("active_lattice"),
        "lattices": manifest_lattices,
        "nca": {"models": {k: rel_to_repo(v) if Path(str(v)).is_absolute() else v for k, v in nca_models.items()}},
        "bridges_file": bridges_rel,
        "bridge_count": len((block.get("bridges") or [])),
    }
    zone_state = _agent_zone_state(block)
    if zone_state:
        manifest["zone_state"] = zone_state
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    if meta.get("intelligence_zones_version") is not None:
        manifest["intelligence_zones_version"] = int(meta["intelligence_zones_version"])
    agent_manifest_path(store_dir).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from casa.prisms.memory.agent_bridges import agent_bridges, save_agent_bridges

    if agent_bridges(state):
        save_agent_bridges(store_dir, state)

    return manifest


def load_agent_prism(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    manifest = _load_manifest(store_dir)
    block = ensure_agent_prism(state)
    lats = agent_lattices(state)

    loaded: list[str] = []
    for lid, meta in (manifest.get("lattices") or {}).items():
        safe_agent_lattice_id(lid)
        rel = meta.get("path") or f"lattices/{lid}.json"
        path = agent_prism_root(store_dir) / rel
        if not path.is_file():
            path = agent_lattice_path(store_dir, lid)
        if path.is_file():
            lats[lid] = json.loads(path.read_text(encoding="utf-8"))
            loaded.append(lid)

    models_in: dict[str, str] = {}
    for lid, raw in ((manifest.get("nca") or {}).get("models") or {}).items():
        p = Path(str(raw))
        if not p.is_absolute():
            p = store_dir / p
        if p.is_file():
            models_in[lid] = str(p.resolve())
    block["nca"] = {"models": models_in}
    if manifest.get("active_lattice"):
        block["active_lattice"] = manifest["active_lattice"]
    _apply_agent_zone_state(block, manifest.get("zone_state"))
    from casa.prisms.affect.zone import consolidate_emotional_zone_wire

    consolidate_emotional_zone_wire(state)
    if manifest.get("intelligence_zones_version") is not None:
        state.setdefault("meta", {})["intelligence_zones_version"] = int(manifest["intelligence_zones_version"])

    genetic_load: dict[str, Any] | None = None
    if (manifest.get("zone_state") or {}).get("genetic_zone") or (agent_prism_root(store_dir) / "genome.v1.json").is_file():
        from casa.prisms.genetic import load_genetic_zone

        genetic_load = load_genetic_zone(store_dir, state)

    from casa.prisms.memory.agent_bridges import load_agent_bridges

    bridge_load = load_agent_bridges(store_dir, state)
    return {
        "loaded_lattices": loaded,
        "nca_models": len(models_in),
        "loaded_bridges": bridge_load.get("loaded", 0),
        "skipped_bridges": bridge_load.get("skipped") or [],
        "genetic": genetic_load,
    }



def main() -> None:
    from casa.prisms.memory.agent_prism_cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()


def train_agent_lattice_nca(*args, **kwargs):
    from casa.prisms.memory.agent_prism_nca import train_agent_lattice_nca as _train

    return _train(*args, **kwargs)
