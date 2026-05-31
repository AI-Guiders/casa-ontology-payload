#!/usr/bin/env python3
"""
Train cluster DMN NCA with module-local damage and spatially weighted loss.

Shared trunk (one UpdateRule per cluster); each batch samples a (bundle, module) parcel.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from layout_apply import _get_region_rect, mask_outside_region  # type: ignore
from module_masks import cell_indices_for_tokens, module_tokens_for_section  # type: ignore
from nca_train_util import (  # type: ignore
    add_device_args,
    configure_cuda,
    damage_tensor_patches,
    grid_indices,
    print_train_device,
    resolve_amp,
    resolve_batch_size,
    empty_cuda_cache,
    resolve_train_device,
    scatter_grid_tensor,
)
from train_dmn_nca import UpdateRule, nca_rollout, nca_rollout_eval, sobel_kernels  # type: ignore
from train_dmn_nca_multibundle import (  # type: ignore
    BundleSpec,
    _grid_to_union_tensor,
    _read_json,
    _threshold_grid_from_union_state,
)


@dataclass(frozen=True)
class ModuleTrainSpec:
    cluster: str
    bundle_path: Path
    bundle: dict
    doc_path: str
    section: str
    section_key: str
    cell_indices: set[int]


def _load_module_specs(
    repo: Path,
    modules_manifest: dict,
    cluster_id: str,
    *,
    concept_mode: str,
) -> list[ModuleTrainSpec]:
    bundle_dir = repo / modules_manifest["bundle_dir"]
    specs: list[ModuleTrainSpec] = []
    from codec_grid_v3 import encode_bundle_to_grid  # type: ignore

    bundle_cache: dict[str, dict] = {}
    grid_cache: dict[str, dict] = {}

    for m in modules_manifest["modules"]:
        if m["cluster"] != cluster_id:
            continue
        bname = m["bundle"]
        if bname not in bundle_cache:
            path = bundle_dir / bname
            bundle_cache[bname] = _read_json(path)
            grid_cache[bname] = encode_bundle_to_grid(bundle_cache[bname], concept_mode=concept_mode)
        bundle = bundle_cache[bname]
        grid = grid_cache[bname]
        toks = module_tokens_for_section(
            bundle,
            doc_path=m["doc_path"],
            section=m["section"],
            concept_mode=concept_mode,
        )
        cells = cell_indices_for_tokens(grid, toks)
        specs.append(
            ModuleTrainSpec(
                cluster=cluster_id,
                bundle_path=bundle_dir / bname,
                bundle=bundle,
                doc_path=m["doc_path"],
                section=m["section"],
                section_key=m["section_key"],
                cell_indices=cells,
            )
        )
    return specs


def main() -> None:
    p = argparse.ArgumentParser(description="Train DMN NCA with module-local supervision")
    p.add_argument("--modules", type=Path, default=Path("manifests/kb-modules.v0.json"))
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--cluster", required=True, help="Cluster id (goals, research, ops)")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damage-patches", type=int, default=6)
    p.add_argument("--patch-w", type=int, default=8)
    p.add_argument("--patch-h", type=int, default=8)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--concept-mode", default="section")
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--concept-radius", type=int, default=5)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--epochs", type=int, default=800)
    add_device_args(p)
    p.add_argument("--hidden", type=int, default=192)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--fire-rate", type=float, default=0.5)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--edge-weight", type=float, default=5.0)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--save-model", action="store_true")
    p.add_argument("--init-model", type=Path, default=None, help="Load weights from prior cluster train (phase 1)")
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.v0.json"))
    p.add_argument("--hard-only", action="store_true", help="Train only modules on hard-tier bundles")
    args = p.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    repo = args.repo_root.resolve()
    modules_manifest = _read_json((repo / args.modules).resolve())
    clusters_manifest = _read_json((repo / args.clusters).resolve())
    bundle_dir = repo / clusters_manifest["bundle_dir"]

    cl = next(c for c in clusters_manifest["clusters"] if c["id"] == args.cluster)
    bundle_paths = sorted({bundle_dir / b for b in cl["bundles"] if (bundle_dir / b).is_file()})
    extra = [repo / b for b in clusters_manifest.get("reference_bundles", []) if (repo / b).is_file()]
    train_paths = sorted(set(bundle_paths + extra), key=lambda p: p.name)

    from codec_grid_v3 import encode_bundle_to_grid as enc_v3, tokens_for_bundle as tok_v3  # type: ignore

    device = resolve_train_device(args.device)
    configure_cuda(device)
    batch_size = resolve_batch_size(args.batch_size, device)
    use_amp = resolve_amp(args.amp, device)
    print_train_device(device, batch_size, use_amp)

    layout = _read_json((repo / args.layout).resolve())
    rect = _get_region_rect(layout, args.region)

    specs_b: list[BundleSpec] = []
    union_tokens: set[str] = set()
    for bp in train_paths:
        b = _read_json(bp)
        toks = set(tok_v3(b, concept_mode=args.concept_mode))
        union_tokens |= toks
        specs_b.append(BundleSpec(path=bp, bundle=b, token_set=toks))

    module_specs = _load_module_specs(repo, modules_manifest, args.cluster, concept_mode=args.concept_mode)
    if args.hard_only:
        tiers = _read_json((repo / args.tiers).resolve())
        hard_names = {
            r["bundle"]
            for r in tiers["bundles"]
            if r["cluster"] == args.cluster and r["tier"] == "hard"
        }
        module_specs = [ms for ms in module_specs if ms.bundle_path.name in hard_names]
        print(f"hard_only modules={len(module_specs)} bundles={sorted(hard_names)}")
    if not module_specs:
        raise SystemExit(f"no modules for cluster {args.cluster}")

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
    module_masks: dict[tuple[str, str], torch.Tensor] = {}
    for s in specs_b:
        full = enc_v3(
            s.bundle,
            width=w,
            height=h,
            copies=args.copies,
            node_radius=args.radius,
            edge_radius=args.edge_radius,
            concept_radius=args.concept_radius,
            concept_mode=args.concept_mode,
        )
        target_grid = mask_outside_region(full, rect)
        idx = grid_indices(target_grid, token_to_i)
        cached_tgt[s.path] = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]

    for ms in module_specs:
        g_path = ms.bundle_path
        if g_path not in cached_tgt:
            continue
        m = torch.zeros(h, w, device=device)
        for idx in ms.cell_indices:
            y, x = idx // w, idx % w
            if rect.contains(x, y):
                m[y, x] = 1.0
        if m.sum() < 1:
            m = torch.ones(h, w, device=device)
        module_masks[(str(g_path), ms.section_key)] = m

    kx, ky = sobel_kernels(device)
    rule = UpdateRule(channel_n=channel_n, hidden=args.hidden).to(device)
    if args.init_model is not None:
        ckpt = torch.load(args.init_model, map_location=device, weights_only=False)
        saved_ids = list(ckpt.get("token_ids") or [])
        if saved_ids != token_ids:
            raise SystemExit(
                f"init-model token_ids mismatch: checkpoint {len(saved_ids)} vs train {len(token_ids)}"
            )
        if int(ckpt.get("channel_n", 0)) != channel_n:
            raise SystemExit(f"init-model channel_n mismatch: {ckpt.get('channel_n')} vs {channel_n}")
        rule.load_state_dict(ckpt["state_dict"])
        print(f"loaded init-model {args.init_model}")
    opt = torch.optim.Adam(rule.parameters(), lr=args.lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_score = -1.0
    best_state: dict | None = None

    for epoch in range(args.epochs):
        batch_tgt: list[torch.Tensor] = []
        batch_inp: list[torch.Tensor] = []
        batch_w: list[torch.Tensor] = []

        for b in range(batch_size):
            ms = module_specs[(epoch * 997 + b * 101) % len(module_specs)]
            tgt_tok = cached_tgt[ms.bundle_path]
            mask = module_masks[(str(ms.bundle_path), ms.section_key)]
            seed = args.seed + epoch * 10007 + b * 97
            inp_tok = damage_tensor_patches(
                tgt_tok,
                rect,
                patch_w=args.patch_w,
                patch_h=args.patch_h,
                count=args.damage_patches,
                seed=seed,
                module_mask=mask,
            )
            batch_tgt.append(tgt_tok)
            batch_inp.append(inp_tok)
            batch_w.append(mask.unsqueeze(0).unsqueeze(0))

        tgt = torch.stack(batch_tgt, dim=0)
        inp = torch.stack(batch_inp, dim=0)
        w_sp = torch.cat(batch_w, dim=0)
        x = torch.zeros(batch_size, channel_n, h, w, device=device)
        x[:, :token_count] = inp

        opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            x = nca_rollout(rule, x, kx, ky, args.steps, args.fire_rate)
            pred = x[:, :token_count]
            diff = (pred - tgt).pow(2)
            weight = w_sp * token_w
            loss = (diff * weight).sum() / weight.sum().clamp(min=1e-6)

        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(rule.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        empty_cuda_cache(device)

        if epoch % 100 == 0 or epoch == args.epochs - 1:
            ms = module_specs[epoch % len(module_specs)]
            tgt_tok = cached_tgt[ms.bundle_path]
            mask = module_masks[(str(ms.bundle_path), ms.section_key)]
            inp = damage_tensor_patches(
                tgt_tok,
                rect,
                patch_w=args.patch_w,
                patch_h=args.patch_h,
                count=args.damage_patches,
                seed=args.seed + 12345,
                module_mask=mask,
            )
            ov = float(mask.mean().item())
            x0 = torch.zeros(1, channel_n, 64, 64, device=device)
            x0[:, :token_count] = inp
            with torch.no_grad():
                xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
                grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=args.threshold)
                decoded = decode_grid(grid_logits, min_votes=args.min_votes)
                score = score_recovery(ms.bundle, decoded)
                mix = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
                if mix > best_score:
                    best_score = mix
                    best_state = {kk: vv.detach().clone() for kk, vv in rule.state_dict().items()}
                print(
                    f"epoch {epoch:4d} loss={loss.item():.6f} module={ms.section_key[:48]} "
                    f"mix={mix:.3f} overlap={ov:.2f}"
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
                "cluster": args.cluster,
                "train_mode": "module_masked_v0",
                "bundles": [str(b) for b in train_paths],
                "module_count": len(module_specs),
            },
            out_model,
        )

    reports = []
    with torch.no_grad():
        for s in specs_b:
            if s.path not in bundle_paths:
                continue
            tgt_tok = cached_tgt[s.path]
            inp = damage_tensor_patches(
                tgt_tok,
                rect,
                patch_w=args.patch_w,
                patch_h=args.patch_h,
                count=args.damage_patches,
                seed=args.seed + 999,
            )
            x0 = torch.zeros(1, channel_n, 64, 64, device=device)
            x0[:, :token_count] = inp
            xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
            grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=args.threshold)
            decoded = decode_grid(grid_logits, min_votes=args.min_votes)
            score = score_recovery(s.bundle, decoded)
            reports.append({"bundle": str(s.path), "score": score})

    out = {
        "schema_version": 1,
        "experiment": "F_module_train_v0",
        "cluster": args.cluster,
        "train_mode": "module_masked_v0",
        "module_count": len(module_specs),
        "layout": str(args.layout),
        "region": args.region,
        "damage_patches": args.damage_patches,
        "epochs": args.epochs,
        "token_count_union": token_count,
        "bundles": [str(b) for b in train_paths],
        "model": str(out_model) if args.save_model else None,
        "reports": reports,
    }
    (args.out_dir / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
