#!/usr/bin/env python3
"""Train NCA repair on core VK lattices (L0_vk_map, L0_grapheme) — GPU by default."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from nca_registry_v0 import repair_smoke_ratio  # type: ignore
from nca_train_defaults_v0 import add_windowed_train_args, damage_defaults, epoch_budget, field_edge  # type: ignore
from nca_train_util import add_device_args, resolve_train_device  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import set_nca_model  # type: ignore
from sss_nca_codec_v0 import tokens_from_lattice  # type: ignore
from store_layout_v0 import nca_lattice_dir  # type: ignore
from field_write import save_field_state  # type: ignore
from vk_layout_field_v0 import VK_CORE_LATTICE_IDS  # type: ignore
from input_modality_ingest_v0 import default_input_modality_bundle, ingest_input_modality  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore
from vk_layout_field_v0 import L0_VK_MAP_ID, imprint_vk_layouts_on_field  # type: ignore

CORE_VK_NCA_LATTICES = (L0_VK_MAP_ID, *VK_CORE_LATTICE_IDS)


def _train_lattice(
    core_dir: Path,
    lattice_id: str,
    *,
    epochs: int,
    device: str,
    windowed: bool,
    tile_w: int,
    tile_h: int,
    stride_x: int,
    stride_y: int,
    ghost: int,
    windows_per_batch: int,
    max_windows_per_batch: int,
    damage_patches: int,
) -> Path:
    out = nca_lattice_dir(core_dir, lattice_id)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        "tools/train_sss_nca_v0.py",
        "--store-dir",
        str(core_dir),
        "--lattice-id",
        lattice_id,
        "--epochs",
        str(epochs),
        "--device",
        device,
        "--out-dir",
        str(out),
        "--save-model",
        "--tile-w",
        str(tile_w),
        "--tile-h",
        str(tile_h),
        "--stride-x",
        str(stride_x),
        "--stride-y",
        str(stride_y),
        "--ghost",
        str(ghost),
        "--windows-per-batch",
        str(windows_per_batch),
        "--max-windows-per-batch",
        str(max_windows_per_batch),
        "--damage-patches",
        str(damage_patches),
    ]
    if not windowed:
        cmd.append("--no-windowed")
    subprocess.run(cmd, check=True, cwd=str(root))
    model = out / "model.pt"
    if not model.is_file():
        raise FileNotFoundError(f"train finished without model: {model}")
    return model


def train_core_vk_nca(
    state: dict,
    core_dir: Path,
    *,
    lattice_ids: tuple[str, ...] = CORE_VK_NCA_LATTICES,
    epochs: int | None = None,
    device: str = "cuda",
    windowed: bool = True,
    tile_w: int | None = None,
    tile_h: int | None = None,
    stride_x: int | None = None,
    stride_y: int | None = None,
    ghost: int | None = None,
    windows_per_batch: int = 0,
    max_windows_per_batch: int = 32,
    damage_patches: int | None = None,
) -> dict[str, Any]:
    """Train repair NCA for VK core lattices; write models under core_dir/nca/."""
    state = ensure_prisms(state)
    core_dir = core_dir.resolve()
    core_dir.mkdir(parents=True, exist_ok=True)
    ep = epochs if epochs is not None else epoch_budget("sss_shard_incremental")
    dmg = damage_defaults()
    edge = field_edge("sss_lattice")
    from nca_train_defaults_v0 import windowed_train_config  # type: ignore

    cfg = windowed_train_config(field_edge=edge)
    tw = tile_w if tile_w is not None else cfg.tile_w
    th = tile_h if tile_h is not None else cfg.tile_h
    sx = stride_x if stride_x is not None else cfg.stride_x
    sy = stride_y if stride_y is not None else cfg.stride_y
    gh = ghost if ghost is not None else cfg.ghost
    dp = damage_patches if damage_patches is not None else dmg["damage_patches"]

    dev = resolve_train_device(device)
    rows: list[dict[str, Any]] = []
    nca_models: dict[str, str] = {}

    for lid in lattice_ids:
        lat = memory_lattices(state).get(lid)
        if not lat or len(tokens_from_lattice(lat)) < 1:
            continue
        model = _train_lattice(
            core_dir,
            lid,
            epochs=ep,
            device=str(dev),
            windowed=windowed,
            tile_w=tw,
            tile_h=th,
            stride_x=sx,
            stride_y=sy,
            ghost=gh,
            windows_per_batch=windows_per_batch,
            max_windows_per_batch=max_windows_per_batch,
            damage_patches=dp,
        )
        set_nca_model(state, lid, str(model.resolve()))
        ratio = repair_smoke_ratio(lat, model)
        rel = f"nca/{lid}/model.pt"
        nca_models[lid] = rel
        rows.append(
            {
                "lattice_id": lid,
                "model_path": str(model),
                "model_rel": rel,
                "repair_ratio": ratio,
                "token_count": len(tokens_from_lattice(lat)),
                "device": str(dev),
                "epochs": ep,
            }
        )

    state.setdefault("nca", {})["core_vk"] = nca_models
    return {
        "core_dir": str(core_dir),
        "device": str(dev),
        "epochs": ep,
        "trained": rows,
        "nca_models": nca_models,
    }


def patch_manifest_nca(core_dir: Path, nca_models: dict[str, str]) -> None:
    manifest_path = core_dir / "ltm" / "pack.manifest.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["nca"] = {
        "schema_version": 1,
        "models": {lid: str(core_dir / rel) for lid, rel in nca_models.items()},
        "models_rel": nca_models,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bootstrap_core_field(core_dir: Path) -> dict:
    import json

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    imprint_vk_layouts_on_field(state)
    bundle = json.loads(default_input_modality_bundle().read_text(encoding="utf-8"))
    ingest_input_modality(state, bundle, ensure_vk_map=False)
    save_field_state(field_state_path(core_dir), state, compact=True)
    return state


def main() -> None:
    _dmg = damage_defaults()
    edge = field_edge("sss_lattice")
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="NCA repair train for core VK lattices (cuda default)")
    p.add_argument(
        "--core-dir",
        type=Path,
        default=root / "lab/agent-core/vk-layouts-v0",
    )
    p.add_argument("--epochs", type=int, default=epoch_budget("sss_shard_incremental"))
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    add_device_args(p)
    p.set_defaults(device="cuda")
    add_windowed_train_args(p, field_edge=edge)
    args = p.parse_args()

    device = "cuda" if args.device in ("auto", "cuda") else args.device
    if device == "cuda":
        resolve_train_device("cuda")
    state = bootstrap_core_field(args.core_dir)
    rep = train_core_vk_nca(
        state,
        args.core_dir,
        epochs=args.epochs,
        device=device,
        windowed=args.windowed,
        tile_w=args.tile_w,
        tile_h=args.tile_h,
        stride_x=args.stride_x,
        stride_y=args.stride_y,
        ghost=args.ghost,
        windows_per_batch=args.windows_per_batch,
        max_windows_per_batch=args.max_windows_per_batch,
        damage_patches=args.damage_patches,
    )
    patch_manifest_nca(args.core_dir, rep["nca_models"])
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
