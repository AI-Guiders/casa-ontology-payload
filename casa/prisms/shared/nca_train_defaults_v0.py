#!/usr/bin/env python3
"""Load canonical NCA train defaults (design/nca-train-defaults.v0.json)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa.prisms.shared.nca_train_core_v0 import WindowedTrainConfig

_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "design" / "nca-train-defaults.v0.json"


@lru_cache(maxsize=1)
def load_nca_train_defaults() -> dict[str, Any]:
    return json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))


def field_edge(name: str) -> int:
    d = load_nca_train_defaults()
    f = d["fields"][name]
    w, h = int(f["width"]), int(f["height"])
    if w != h:
        raise ValueError(f"field {name!r}: expected square, got {w}x{h}")
    return w


def windowed_dims(*, field_edge: int) -> dict[str, int]:
    d = load_nca_train_defaults()
    key = str(int(field_edge))
    by = d["windowed"]["by_field_edge"]
    if key not in by:
        raise KeyError(f"no windowed.by_field_edge[{key!r}] in {_DEFAULTS_PATH.name}")
    return {k: int(v) for k, v in by[key].items()}


def windowed_train_config(*, field_edge: int) -> WindowedTrainConfig:
    d = load_nca_train_defaults()
    w = d["windowed"]
    dims = windowed_dims(field_edge=field_edge)
    return WindowedTrainConfig(
        tile_w=dims["tile_w"],
        tile_h=dims["tile_h"],
        stride_x=dims["stride_x"],
        stride_y=dims["stride_y"],
        ghost=int(w["ghost"]),
        windows_per_batch=int(w["windows_per_batch"]),
        max_windows_per_batch=int(w["max_windows_per_batch"]),
    )


def damage_defaults() -> dict[str, int]:
    dmg = load_nca_train_defaults()["damage"]
    return {
        "damage_patches": int(dmg["patches"]),
        "patch_w": int(dmg["patch_w"]),
        "patch_h": int(dmg["patch_h"]),
    }


def nca_profile(name: str) -> dict[str, Any]:
    return dict(load_nca_train_defaults()["nca"][name])


def epoch_budget(key: str) -> int:
    return int(load_nca_train_defaults()["epochs"][key])


def cuda_batch_size_full() -> int:
    return int(load_nca_train_defaults()["device_cuda"]["batch_size_full"])


def add_windowed_train_args(
    p: argparse.ArgumentParser,
    *,
    field_edge: int,
    windowed_default: bool = True,
) -> None:
    """CLI flags defaulting to tuned window geometry for ``field_edge`` (32 or 64)."""
    cfg = windowed_train_config(field_edge=field_edge)
    g = p.add_argument_group("windowed (canonical defaults from nca-train-defaults.v0.json)")
    g.add_argument(
        "--windowed",
        action=argparse.BooleanOptionalAction,
        default=windowed_default,
        help="Sliding windows + ghost + masked loss (default on for production train).",
    )
    g.add_argument("--tile-w", type=int, default=cfg.tile_w)
    g.add_argument("--tile-h", type=int, default=cfg.tile_h)
    g.add_argument("--stride-x", type=int, default=cfg.stride_x)
    g.add_argument("--stride-y", type=int, default=cfg.stride_y)
    g.add_argument("--ghost", type=int, default=cfg.ghost)
    g.add_argument("--windows-per-batch", type=int, default=cfg.windows_per_batch)
    g.add_argument("--max-windows-per-batch", type=int, default=cfg.max_windows_per_batch)
    prof = nca_profile("dmn" if field_edge >= 64 else "sss")
    g.add_argument(
        "--edge-weight",
        type=float,
        default=float(prof.get("edge_weight", 1.0)),
        help="MSE weight for E:* tokens (DMN); 1.0 for SSS W:* lattices",
    )
