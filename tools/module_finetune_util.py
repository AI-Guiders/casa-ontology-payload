#!/usr/bin/env python3
"""Short module finetune after knowledge_delta import (vocab expand + local loss)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from layout_apply import _get_region_rect, mask_outside_region  # type: ignore
from module_masks import cell_indices_for_tokens, module_tokens_for_section  # type: ignore
from nca_train_util import (  # type: ignore
    configure_cuda,
    damage_tensor_patches,
    empty_cuda_cache,
    grid_indices,
    resolve_amp,
    resolve_batch_size,
    resolve_train_device,
    scatter_grid_tensor,
)
from train_dmn_nca import UpdateRule, nca_rollout, nca_rollout_eval, sobel_kernels  # type: ignore
from train_dmn_nca_multibundle import BundleSpec, _read_json, _threshold_grid_from_union_state  # type: ignore
from train_module_nca import ModuleTrainSpec  # type: ignore


def expand_rule_for_vocab(
    ckpt: dict,
    new_token_ids: list[str],
    *,
    hidden: int | None = None,
) -> tuple[UpdateRule, list[str], int]:
    """Grow UpdateRule when import added tokens; copy overlapping channels."""
    old_ids = list(ckpt["token_ids"])
    old_ch = int(ckpt["channel_n"])
    old_k = len(old_ids)
    new_k = len(new_token_ids)
    h_dm = old_ch - old_k
    new_ch = new_k + h_dm
    hid = hidden or int(ckpt.get("hidden", 192))

    old_rule = UpdateRule(old_ch, hid)
    old_rule.load_state_dict(ckpt["state_dict"])
    new_rule = UpdateRule(new_ch, hid)

    w0_old = old_rule.fc0.weight.data
    b0_old = old_rule.fc0.bias.data
    w1_old = old_rule.fc1.weight.data

    w0_new = new_rule.fc0.weight.data.zero_()
    new_rule.fc0.bias.data.copy_(b0_old)
    w1_new = new_rule.fc1.weight.data.zero_()

    def _copy_channel(old_i: int, new_i: int) -> None:
        for p in range(3):
            w0_new[:, new_i * 3 + p] = w0_old[:, old_i * 3 + p]
        w1_new[new_i] = w1_old[old_i]

    old_index = {t: i for i, t in enumerate(old_ids)}
    for t, old_i in old_index.items():
        if t in new_token_ids:
            new_i = new_token_ids.index(t)
            _copy_channel(old_i, new_i)

    for j in range(h_dm):
        _copy_channel(old_k + j, new_k + j)

    return new_rule, new_token_ids, new_ch


@dataclass(frozen=True)
class FinetuneResult:
    model_path: Path
    token_count: int
    epochs: int
    best_mix: float
    modules: list[str]


def finetune_after_import(
    *,
    repo: Path,
    cluster: str,
    bundle_name: str,
    store_bundle_path: Path,
    init_ckpt: Path,
    out_ckpt: Path,
    module_ids: list[str] | None = None,
    epochs: int = 120,
    seed: int = 7,
    device_name: str = "auto",
) -> FinetuneResult:
    from codec_grid_v3 import encode_bundle_to_grid as enc_v3, tokens_for_bundle as tok_v3  # type: ignore
    from codec_grid_v0 import decode_grid, score_recovery  # type: ignore

    modules_manifest = _read_json(repo / "manifests/kb-modules.v0.json")
    clusters_manifest = _read_json(repo / "manifests/kb-clusters.v0.json")
    layout = _read_json(repo / "design/layout.v0.json")
    rect = _get_region_rect(layout, "dmn_ontology")
    concept_mode = modules_manifest.get("concept_mode", "section")

    cl = next(c for c in clusters_manifest["clusters"] if c["id"] == cluster)
    bundle_dir = repo / clusters_manifest["bundle_dir"]

    train_paths: list[Path] = []
    for b in cl["bundles"]:
        if b == bundle_name:
            train_paths.append(store_bundle_path)
        else:
            p = bundle_dir / b
            if p.is_file():
                train_paths.append(p)
    for ref in clusters_manifest.get("reference_bundles", []):
        p = repo / ref
        if p.is_file():
            train_paths.append(p)
    train_paths = sorted(set(train_paths), key=lambda p: p.name)

    specs_b: list[BundleSpec] = []
    union_tokens: set[str] = set()
    bundle_by_path: dict[Path, dict] = {}
    for bp in train_paths:
        b = _read_json(bp)
        bundle_by_path[bp] = b
        toks = set(tok_v3(b, concept_mode=concept_mode))
        union_tokens |= toks
        specs_b.append(BundleSpec(path=bp, bundle=b, token_set=toks))

    id_set = set(module_ids or [])
    all_module_specs: list[ModuleTrainSpec] = []
    grid_cache: dict[Path, dict] = {}
    for m in modules_manifest["modules"]:
        if m["cluster"] != cluster:
            continue
        bname = m["bundle"]
        if bname == bundle_name:
            bp = store_bundle_path
        else:
            bp = bundle_dir / bname
        if not bp.is_file():
            continue
        bundle = bundle_by_path.get(bp) or _read_json(bp)
        if bp not in grid_cache:
            grid_cache[bp] = enc_v3(bundle, concept_mode=concept_mode)
        grid = grid_cache[bp]
        toks = module_tokens_for_section(
            bundle,
            doc_path=m["doc_path"],
            section=m["section"],
            concept_mode=concept_mode,
        )
        cells = cell_indices_for_tokens(grid, toks)
        all_module_specs.append(
            ModuleTrainSpec(
                cluster=cluster,
                bundle_path=bp,
                bundle=bundle,
                doc_path=m["doc_path"],
                section=m["section"],
                section_key=m["section_key"],
                cell_indices=cells,
            )
        )

    if id_set:
        by_id = [
            ms
            for ms in all_module_specs
            for mod in modules_manifest["modules"]
            if mod["id"] in id_set and mod["section_key"] == ms.section_key and mod["bundle"] == bundle_name
        ]
        module_specs = by_id if by_id else [ms for ms in all_module_specs if ms.bundle_path.name == bundle_name]
    else:
        module_specs = [ms for ms in all_module_specs if ms.bundle_path.name == bundle_name]

    if not module_specs:
        raise RuntimeError(f"no modules to finetune for {bundle_name}")

    token_ids = sorted(union_tokens)
    k = len(token_ids)
    channel_n = k + 8

    device = resolve_train_device(device_name)
    configure_cuda(device)
    batch_size = resolve_batch_size(0, device)
    use_amp = resolve_amp(None, device)

    ckpt = torch.load(init_ckpt, map_location="cpu", weights_only=False)
    if list(ckpt["token_ids"]) == token_ids and int(ckpt["channel_n"]) == channel_n:
        rule = UpdateRule(channel_n, int(ckpt["hidden"])).to(device)
        rule.load_state_dict(ckpt["state_dict"])
    else:
        rule, token_ids, channel_n = expand_rule_for_vocab(ckpt, token_ids, hidden=int(ckpt.get("hidden", 192)))
        rule = rule.to(device)
        k = len(token_ids)

    token_w = torch.ones(k, device=device)
    for i, t in enumerate(token_ids):
        if t.startswith("E:"):
            token_w[i] = 5.0
    token_w = token_w.view(1, k, 1, 1)

    h, w = 64, 64
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    cached_tgt: dict[Path, torch.Tensor] = {}
    for s in specs_b:
        full = enc_v3(s.bundle, width=w, height=h, copies=7, concept_mode=concept_mode)
        target_grid = mask_outside_region(full, rect)
        idx = grid_indices(target_grid, token_to_i)
        cached_tgt[s.path] = scatter_grid_tensor(idx, k=k, h=h, w=w, device=device)[0]

    module_masks: dict[tuple[str, str], torch.Tensor] = {}
    for ms in module_specs:
        m = torch.zeros(h, w, device=device)
        for idx in ms.cell_indices:
            y, x = idx // w, idx % w
            if rect.contains(x, y):
                m[y, x] = 1.0
        if m.sum() < 1:
            m = torch.ones(h, w, device=device)
        module_masks[(str(ms.bundle_path), ms.section_key)] = m

    random.seed(seed)
    torch.manual_seed(seed)
    np.random.seed(seed)

    kx, ky = sobel_kernels(device)
    opt = torch.optim.Adam(rule.parameters(), lr=3e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_score = -1.0
    best_state: dict | None = None
    steps, fire_rate, patch_count = 48, 0.5, 6

    for epoch in range(epochs):
        batch_tgt, batch_inp, batch_w = [], [], []
        for b in range(batch_size):
            ms = module_specs[(epoch * 997 + b * 101) % len(module_specs)]
            tgt_tok = cached_tgt[ms.bundle_path]
            mask = module_masks[(str(ms.bundle_path), ms.section_key)]
            inp_tok = damage_tensor_patches(
                tgt_tok,
                rect,
                patch_w=8,
                patch_h=8,
                count=patch_count,
                seed=seed + epoch * 10007 + b * 97,
                module_mask=mask,
            )
            batch_tgt.append(tgt_tok)
            batch_inp.append(inp_tok)
            batch_w.append(mask.unsqueeze(0).unsqueeze(0))

        tgt = torch.stack(batch_tgt, dim=0)
        inp = torch.stack(batch_inp, dim=0)
        w_sp = torch.cat(batch_w, dim=0)
        x = torch.zeros(batch_size, channel_n, h, w, device=device)
        x[:, :k] = inp

        opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            x = nca_rollout(rule, x, kx, ky, steps, fire_rate)
            diff = (x[:, :k] - tgt).pow(2)
            weight = w_sp * token_w
            loss = (diff * weight).sum() / weight.sum().clamp(min=1e-6)

        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(rule.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        empty_cuda_cache(device)

        if epoch % 40 == 0 or epoch == epochs - 1:
            ms = module_specs[epoch % len(module_specs)]
            tgt_tok = cached_tgt[ms.bundle_path]
            mask = module_masks[(str(ms.bundle_path), ms.section_key)]
            inp = damage_tensor_patches(
                tgt_tok,
                rect,
                patch_w=8,
                patch_h=8,
                count=patch_count,
                seed=seed + 12345,
                module_mask=mask,
            )
            x0 = torch.zeros(1, channel_n, h, w, device=device)
            x0[:, :k] = inp
            with torch.no_grad():
                xT = nca_rollout_eval(rule, x0, kx, ky, steps=steps)
                grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=0.5)
                decoded = decode_grid(grid_logits, min_votes=3)
                score = score_recovery(ms.bundle, decoded)
                mix = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
                if mix > best_score:
                    best_score = mix
                    best_state = {kk: vv.detach().clone() for kk, vv in rule.state_dict().items()}

    if best_state is not None:
        rule.load_state_dict(best_state)

    out_ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "schema_version": 1,
            "channel_n": channel_n,
            "token_ids": token_ids,
            "hidden": int(ckpt.get("hidden", 192)),
            "steps": steps,
            "fire_rate_train": fire_rate,
            "state_dict": rule.state_dict(),
            "cluster": cluster,
            "finetune": True,
            "source_init": str(init_ckpt),
        },
        out_ckpt,
    )

    mod_ids: list[str] = []
    seen: set[str] = set()
    for mod in modules_manifest["modules"]:
        for ms in module_specs:
            if mod["section_key"] == ms.section_key and mod["bundle"] == bundle_name:
                if mod["id"] not in seen:
                    mod_ids.append(mod["id"])
                    seen.add(mod["id"])

    return FinetuneResult(
        model_path=out_ckpt,
        token_count=len(token_ids),
        epochs=epochs,
        best_mix=best_score,
        modules=mod_ids[:8],
    )
