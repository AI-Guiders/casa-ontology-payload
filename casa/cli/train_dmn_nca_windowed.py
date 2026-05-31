#!/usr/bin/env python3
"""
Train DMN NCA with sliding windows: each step runs the same local rule on a tile crop.

Uses FieldPlannerV0 to sample dense tiles; loss is masked to tile interior only.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch

from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from field_planner_v0 import FieldPlannerV0  # type: ignore
from field_window import Tile, crop_canvas_size, extract_window_crop, loss_mask_padded  # type: ignore
from layout_apply import _get_region_rect, mask_outside_region  # type: ignore
from nca_train_util import (  # type: ignore
    add_device_args,
    configure_cuda,
    damage_tensor_patches,
    grid_indices,
    print_train_device,
    resolve_amp,
    empty_cuda_cache,
    resolve_train_device,
    resolve_windows_per_batch,
    scatter_grid_tensor,
)
from nca_train_defaults_v0 import (  # type: ignore
    add_windowed_train_args,
    damage_defaults,
    epoch_budget,
    field_edge,
    nca_profile,
)
from train_dmn_nca import UpdateRule, nca_rollout, sobel_kernels  # type: ignore
from train_dmn_nca_multibundle import (  # type: ignore
    BundleSpec,
    _read_json,
    _threshold_grid_from_union_state,
    _tokens_for_bundle,
)


def main() -> None:
    _dmn = nca_profile("dmn")
    _dmg = damage_defaults()
    _fe = field_edge("dmn")

    p = argparse.ArgumentParser(description="Windowed DMN NCA train (multibundle)")
    p.add_argument("--bundles", nargs="+", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    add_windowed_train_args(p, field_edge=_fe, windowed_default=True)
    p.add_argument(
        "--windows-per-sample",
        type=int,
        default=0,
        help="Deprecated alias for --windows-per-batch; ignored if windows-per-batch > 0.",
    )
    p.add_argument("--damage-mode", choices=["drop", "patches"], default="patches")
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    p.add_argument("--patch-w", type=int, default=_dmg["patch_w"])
    p.add_argument("--patch-h", type=int, default=_dmg["patch_h"])
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--codec", choices=["v0", "v1", "v2", "v3"], default="v3")
    p.add_argument("--concept-mode", choices=["independent", "doc", "section", "doc_section"], default="section")
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--concept-radius", type=int, default=5)
    p.add_argument("--steps", type=int, default=int(_dmn["steps"]))
    p.add_argument("--epochs", type=int, default=epoch_budget("dmn_union_full"))
    add_device_args(p)
    p.add_argument("--hidden", type=int, default=int(_dmn["hidden"]))
    p.add_argument("--lr", type=float, default=float(_dmn["lr"]))
    p.add_argument("--fire-rate", type=float, default=float(_dmn["fire_rate"]))
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out-dir", type=Path, default=Path("lab/nca_out_exp_j_ru_windowed_v1"))
    p.add_argument("--save-model", action="store_true")
    args = p.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = resolve_train_device(args.device)
    configure_cuda(device)
    use_amp = resolve_amp(args.amp, device)
    canvas_h, canvas_w = crop_canvas_size(args.tile_w, args.tile_h, args.ghost)
    win_batch = args.windows_per_batch
    if win_batch <= 0 and args.windows_per_sample > 0:
        win_batch = args.windows_per_sample
    win_batch = resolve_windows_per_batch(
        win_batch,
        device,
        crop_h=canvas_h,
        crop_w=canvas_w,
        max_windows=args.max_windows_per_batch,
    )
    print_train_device(device, win_batch, use_amp)
    print(
        f"windowed tile={args.tile_w}x{args.tile_h} stride={args.stride_x},{args.stride_y} "
        f"ghost={args.ghost} canvas={canvas_w}x{canvas_h} windows_per_batch={win_batch} (parallel)"
    )

    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    encode_bundle_to_grid = None
    if args.codec == "v3":
        from codec_grid_v3 import encode_bundle_to_grid as _enc_v3, tokens_for_bundle as _tok_v3  # type: ignore

        def encode_bundle_to_grid(bundle: dict, **kw):  # type: ignore[no-redef]
            return _enc_v3(bundle, concept_mode=args.concept_mode, **kw)

        _tokens_for_bundle_fn = lambda b: _tok_v3(b, concept_mode=args.concept_mode)
    elif args.codec == "v2":
        from codec_grid_v2 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle
    elif args.codec == "v1":
        from codec_grid_v1 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle
    else:
        from codec_grid_v0 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle

    specs: list[BundleSpec] = []
    union_tokens: set[str] = set()
    for bp in args.bundles:
        b = _read_json(bp)
        toks = set(_tokens_for_bundle_fn(b))
        union_tokens |= toks
        specs.append(BundleSpec(path=bp, bundle=b, token_set=toks))

    token_ids = sorted(union_tokens)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    token_count = len(token_ids)
    channel_n = token_count + 8

    token_w = torch.ones(token_count, device=device)
    if args.edge_weight != 1.0:
        for i, t in enumerate(token_ids):
            if t.startswith("E:"):
                token_w[i] = float(args.edge_weight)
    token_w = token_w.view(1, token_count, 1, 1)

    h, w = 64, 64
    cached_tgt: dict[Path, torch.Tensor] = {}
    planners: dict[Path, FieldPlannerV0] = {}
    for s in specs:
        if args.codec == "v3":
            full = encode_bundle_to_grid(
                s.bundle,
                width=w,
                height=h,
                copies=args.copies,
                node_radius=args.radius,
                edge_radius=args.edge_radius,
                concept_radius=args.concept_radius,
            )
        elif args.codec == "v2":
            full = encode_bundle_to_grid(
                s.bundle,
                width=w,
                height=h,
                copies=args.copies,
                node_radius=args.radius,
                edge_radius=args.edge_radius,
            )
        elif args.codec == "v1":
            full = encode_bundle_to_grid(s.bundle, width=w, height=h, copies=args.copies, radius=args.radius)
        else:
            full = encode_bundle_to_grid(s.bundle, width=w, height=h, copies=args.copies)
        target_grid = mask_outside_region(full, rect)
        idx = grid_indices(target_grid, token_to_i)
        tgt = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]
        cached_tgt[s.path] = tgt
        planners[s.path] = FieldPlannerV0.from_field_tensor(
            tgt,
            rect,
            tile_w=args.tile_w,
            tile_h=args.tile_h,
            stride_x=args.stride_x,
            stride_y=args.stride_y,
        )

    union_planner = FieldPlannerV0.from_bundles_union(
        list(cached_tgt.values()),
        rect,
        tile_w=args.tile_w,
        tile_h=args.tile_h,
        stride_x=args.stride_x,
        stride_y=args.stride_y,
    )
    planner_summary = union_planner.summary()
    print(f"planner: {json.dumps(planner_summary, ensure_ascii=False)}")

    kx, ky = sobel_kernels(device)
    rule = UpdateRule(channel_n=channel_n, hidden=args.hidden).to(device)
    opt = torch.optim.Adam(rule.parameters(), lr=args.lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_score = -1.0
    best_state: dict | None = None
    import time as _time

    train_t0 = _time.perf_counter()

    for epoch in range(args.epochs):
        sampled = union_planner.sample_train_tiles(win_batch, epoch=epoch, seed=args.seed)
        crops_t: list[torch.Tensor] = []
        crops_i: list[torch.Tensor] = []
        masks: list[torch.Tensor] = []

        for wi, tile in enumerate(sampled):
            spec = specs[(epoch * 997 + wi * 101) % len(specs)]
            tgt_full = cached_tgt[spec.path]
            seed = args.seed + epoch * 10007 + wi * 131
            if args.damage_mode == "patches":
                damaged = damage_tensor_patches(
                    tgt_full,
                    tile.to_rect(),
                    patch_w=args.patch_w,
                    patch_h=args.patch_h,
                    count=args.damage_patches,
                    seed=seed,
                )
            else:
                damaged = tgt_full.clone()
                damaged[:, tile.y0 : tile.y0 + tile.h, tile.x0 : tile.x0 + tile.w] = 0.0

            crop_t, fx0, fy0 = extract_window_crop(
                tgt_full,
                tile,
                args.ghost,
                canvas_h=canvas_h,
                canvas_w=canvas_w,
            )
            crop_i, _, _ = extract_window_crop(
                damaged,
                tile,
                args.ghost,
                canvas_h=canvas_h,
                canvas_w=canvas_w,
            )
            crops_t.append(crop_t)
            crops_i.append(crop_i)
            masks.append(loss_mask_padded(canvas_h, canvas_w, tile, fx0, fy0, device))

        opt.zero_grad(set_to_none=True)
        tgt_b = torch.stack(crops_t, dim=0)
        inp_b = torch.stack(crops_i, dim=0)
        mask_b = torch.cat(masks, dim=0)
        x = torch.zeros(win_batch, channel_n, canvas_h, canvas_w, device=device)
        x[:, :token_count] = inp_b

        with torch.autocast(device_type=device.type, enabled=use_amp):
            x = nca_rollout(rule, x, kx, ky, args.steps, args.fire_rate)
            pred = x[:, :token_count]
            diff = (pred - tgt_b).pow(2) * token_w
            denom = mask_b.sum().clamp(min=1.0)
            loss = (diff * mask_b).sum() / denom

        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(rule.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        loss_val = float(loss.item())
        empty_cuda_cache(device)

        if epoch % 100 == 0 or epoch == args.epochs - 1:
            from repair_dmn_nca_windowed import repair_field_windowed  # type: ignore

            spec = specs[epoch % len(specs)]
            planner = planners[spec.path]
            with torch.no_grad():
                pred_tok = repair_field_windowed(
                    rule,
                    cached_tgt[spec.path],
                    planner,
                    token_channels=token_count,
                    channel_n=channel_n,
                    kx=kx,
                    ky=ky,
                    steps=args.steps,
                    ghost=args.ghost,
                    device=device,
                    damage_seed=args.seed + 12345,
                    damage_patches=args.damage_patches,
                    patch_w=args.patch_w,
                    patch_h=args.patch_h,
                    tile_w=args.tile_w,
                    tile_h=args.tile_h,
                    batched=True,
                )
                grid_logits = _threshold_grid_from_union_state(
                    pred_tok.unsqueeze(0),
                    token_ids=token_ids,
                    threshold=args.threshold,
                )
                decoded = decode_grid(grid_logits, min_votes=args.min_votes)
                score = score_recovery(spec.bundle, decoded)
                mix = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
                if mix > best_score:
                    best_score = mix
                    best_state = {kk: vv.detach().clone() for kk, vv in rule.state_dict().items()}
                print(
                    f"epoch {epoch:4d} loss={loss_val:.6f} eval_bundle={spec.path.name} mix={mix:.3f} "
                    f"c={score['concepts']['f1']:.3f} e={score['edges']['f1']:.3f} (windowed eval)"
                )

    if best_state is not None:
        rule.load_state_dict(best_state)

    out_model = args.out_dir / "model.pt"
    if args.save_model:
        torch.save(
            {
                "schema_version": 1,
                "channel_n": channel_n,
                "token_ids": token_ids,
                "hidden": args.hidden,
                "steps": args.steps,
                "fire_rate_train": args.fire_rate,
                "state_dict": rule.state_dict(),
                "bundles": [str(b) for b in args.bundles],
                "train_mode": "windowed",
                "tile_w": args.tile_w,
                "tile_h": args.tile_h,
                "stride_x": args.stride_x,
                "stride_y": args.stride_y,
                "ghost": args.ghost,
                "windows_per_batch": win_batch,
                "canvas_h": canvas_h,
                "canvas_w": canvas_w,
            },
            out_model,
        )

    train_sec = _time.perf_counter() - train_t0
    print(f"Train wall-clock: {train_sec:.1f}s ({train_sec / 60:.2f} min)")

    out = {
        "schema_version": 1,
        "train_mode": "windowed_batched",
        "train_wall_sec": train_sec,
        "planner": planner_summary,
        "tile_w": args.tile_w,
        "tile_h": args.tile_h,
        "stride_x": args.stride_x,
        "stride_y": args.stride_y,
        "ghost": args.ghost,
        "windows_per_batch": win_batch,
        "canvas_h": canvas_h,
        "canvas_w": canvas_w,
        "epochs": args.epochs,
        "token_count_union": token_count,
        "bundles": [str(b) for b in args.bundles],
        "model": str(out_model) if args.save_model else None,
        "best_mix": best_score,
    }
    (args.out_dir / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
