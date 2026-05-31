#!/usr/bin/env python3
"""Agent-owned memory prism — lattices + NCA outside profile ltm/ export."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_core import NcaTrainerConfig, WindowedTrainConfig, run_nca_training
from casa.prisms.shared.nca_train_defaults import damage_defaults, epoch_budget, field_edge, nca_profile
from casa.prisms.shared.nca_train_util import damage_tensor_patches, grid_indices, resolve_train_device, scatter_grid_tensor
from casa.prisms.shared.prism_state import PRISM_AGENT, normalize_prisms, prism_agent, set_active_prism
from casa.prisms.shared.store_layout import (
    agent_bridges_path,
    agent_lattice_path,
    agent_lattices_dir,
    agent_manifest_path,
    agent_nca_lattice_dir,
    agent_prism_root,
    field_state_path,
    rel_to_repo,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.nca_codec import lattice_as_grid, tokens_from_lattice
from casa.prisms.memory.stack import _place_token, decode_lattice
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels

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


def save_agent_prism(store_dir: Path, state: dict) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    ensure_agent_prism(state)
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

    from casa.prisms.memory.agent_bridges import load_agent_bridges

    bridge_load = load_agent_bridges(store_dir, state)
    return {
        "loaded_lattices": loaded,
        "nca_models": len(models_in),
        "loaded_bridges": bridge_load.get("loaded", 0),
        "skipped_bridges": bridge_load.get("skipped") or [],
    }


def train_agent_lattice_nca(
    state: dict,
    store_dir: Path,
    lattice_id: str,
    *,
    epochs: int | None = None,
    device: str = "auto",
    seed: int = 1,
) -> dict[str, Any]:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid not in lats:
        raise KeyError(f"unknown agent lattice: {lid}")
    lattice = lats[lid]

    token_ids = tokens_from_lattice(lattice)
    if not token_ids:
        raise ValueError(f"lattice {lid} has no tokens to train on")

    profile = nca_profile("sss")
    dmg = damage_defaults()
    fe = field_edge("sss_lattice")
    ep = epoch_budget("sss_shard_incremental") if epochs is None else int(epochs)

    torch.manual_seed(seed)
    np.random.seed(seed)
    dev = resolve_train_device(device)

    grid = lattice_as_grid(lattice)
    token_count = len(token_ids)
    channel_n = token_count + 6
    h = int(grid["height"])
    w = int(grid["width"])
    rect = Rect(x0=0, y0=0, x1=w - 1, y1=h - 1)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    tgt_tok = scatter_grid_tensor(grid_indices(grid, token_to_i), token_channels=token_count, h=h, w=w, device=dev)[0]

    train_cfg = NcaTrainerConfig(
        token_channels=token_count,
        h=h,
        w=w,
        hidden=int(profile["hidden"]),
        channel_extra=6,
        steps=int(profile["steps"]),
        epochs=ep,
        lr=float(profile["lr"]),
        fire_rate=float(profile["fire_rate"]),
        damage_patches=int(dmg["damage_patches"]),
        patch_w=int(dmg["patch_w"]),
        patch_h=int(dmg["patch_h"]),
        seed=seed,
        device=device,
    )
    win_cfg = WindowedTrainConfig(
        tile_w=fe["tile_w"],
        tile_h=fe["tile_h"],
        stride_x=fe["stride_x"],
        stride_y=fe["stride_y"],
        ghost=fe["ghost"],
        windows_per_batch=fe["windows_per_batch"],
        max_windows_per_batch=fe["max_windows_per_batch"],
        edge_weight=fe["edge_weight"],
    )
    run = run_nca_training(train_cfg, tgt=tgt_tok, rect=rect, mode="windowed", windowed=win_cfg)
    rule = UpdateRule(channel_n=channel_n, hidden=int(profile["hidden"])).to(dev)
    rule.load_state_dict(run.state_dict)

    out_dir = agent_nca_lattice_dir(store_dir, lid)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "model.pt"
    torch.save(
        {
            "schema_version": 1,
            "kind": "agent_lattice_nca",
            "lattice_id": lid,
            "channel_n": channel_n,
            "token_ids": token_ids,
            "width": w,
            "height": h,
            "hidden": int(profile["hidden"]),
            "steps": int(profile["steps"]),
            "fire_rate_train": float(profile["fire_rate"]),
            "state_dict": rule.state_dict(),
        },
        model_path,
    )

    kx, ky = sobel_kernels(dev)
    with torch.no_grad():
        eval_inp = damage_tensor_patches(
            tgt_tok,
            rect,
            patch_w=int(dmg["patch_w"]),
            patch_h=int(dmg["patch_h"]),
            count=int(dmg["damage_patches"]),
            seed=seed + 999,
        )
        seed_t = torch.zeros(1, channel_n, h, w, device=dev)
        seed_t[:, :token_count] = eval_inp.unsqueeze(0)
        final_x = nca_rollout_eval(rule, seed_t, kx, ky, int(profile["steps"]))

    block = ensure_agent_prism(state)
    block.setdefault("nca", {}).setdefault("models", {})[lid] = str(model_path.resolve())
    state["field_version"] = int(state.get("field_version") or 0) + 1

    return {
        "lattice_id": lid,
        "epochs": ep,
        "best_loss": run.best_loss,
        "model_path": str(model_path),
        "token_count": token_count,
        "eval_max_activation": float(final_x.max().cpu()),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Agent-owned prism — lattices + NCA outside profile ltm/")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)

    sp_create = sub.add_parser("create-lattice")
    add_store(sp_create)
    sp_create.add_argument("--id", required=True, dest="lattice_id")
    sp_create.add_argument("--width", type=int, default=32)
    sp_create.add_argument("--height", type=int, default=32)
    sp_create.add_argument("--z-level", type=int, default=0)
    sp_create.add_argument("--write", action="store_true")

    sp_place = sub.add_parser("place")
    add_store(sp_place)
    sp_place.add_argument("--lattice", required=True)
    sp_place.add_argument("--token", required=True)
    sp_place.add_argument("--x", type=int, default=None)
    sp_place.add_argument("--y", type=int, default=None)
    sp_place.add_argument("--copies", type=int, default=1)
    sp_place.add_argument("--write", action="store_true")

    sp_list = sub.add_parser("list")
    add_store(sp_list)

    sp_read = sub.add_parser("read")
    add_store(sp_read)
    sp_read.add_argument("--lattice", required=True)

    sp_delete = sub.add_parser("delete-lattice")
    add_store(sp_delete)
    sp_delete.add_argument("--lattice", required=True)
    sp_delete.add_argument("--write", action="store_true")

    sp_train = sub.add_parser("train-nca")
    add_store(sp_train)
    sp_train.add_argument("--lattice", required=True)
    sp_train.add_argument("--epochs", type=int, default=None)
    sp_train.add_argument("--device", default="auto")
    sp_train.add_argument("--write", action="store_true")

    sp_save = sub.add_parser("save")
    add_store(sp_save)

    sp_load = sub.add_parser("load")
    add_store(sp_load)

    sp_active = sub.add_parser("activate")
    add_store(sp_active)
    sp_active.add_argument("--lattice", required=True)
    sp_active.add_argument("--write", action="store_true")

    args = p.parse_args()
    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    load_agent_prism(store_dir, state)

    out: Any = None

    if args.cmd == "create-lattice":
        out = create_agent_lattice(
            state,
            args.lattice_id,
            width=args.width,
            height=args.height,
            z_level=args.z_level,
        )
    elif args.cmd == "place":
        out = place_agent_token(state, args.lattice, args.token, x=args.x, y=args.y, copies=args.copies)
    elif args.cmd == "list":
        out = {"lattices": list_agent_lattices(state), "active_prism": PRISM_AGENT}
    elif args.cmd == "read":
        out = read_agent_lattice(state, args.lattice)
    elif args.cmd == "delete-lattice":
        ok = delete_agent_lattice(state, args.lattice)
        out = {"deleted": ok, "lattice_id": args.lattice}
        if not ok:
            raise SystemExit(1)
    elif args.cmd == "train-nca":
        out = train_agent_lattice_nca(state, store_dir, args.lattice, epochs=args.epochs, device=args.device)
    elif args.cmd == "save":
        out = save_agent_prism(store_dir, state)
    elif args.cmd == "load":
        out = load_agent_prism(store_dir, state)
    elif args.cmd == "activate":
        safe_agent_lattice_id(args.lattice)
        if args.lattice not in agent_lattices(state):
            raise SystemExit(f"unknown agent lattice: {args.lattice}")
        prism_agent(state)["active_lattice"] = args.lattice
        set_active_prism(state, PRISM_AGENT)
        state["sn"] = {**(state.get("sn") or {}), "active_lattice": args.lattice}
        out = {"active_prism": PRISM_AGENT, "active_lattice": args.lattice}

    write = getattr(args, "write", False) or args.cmd in ("save",)
    if write and args.cmd != "load":
        save_agent_prism(store_dir, state)
        if fs.parent.exists():
            save_field_state(fs, state, compact=True)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
