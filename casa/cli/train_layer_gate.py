#!/usr/bin/env python3
"""Train z=gate layer (SN) from digest channels; DMN+digest frozen."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn

from casa.prisms.shared.canonical import CANONICAL_CONCEPT_MODE
from casa.prisms.shared.layout_apply import _get_region_rect, damage_region_patches, mask_outside_region
from casa.prisms.shared.layered_nca_core import (
    LayeredChannelLayout,
    build_digest_target,
    channel_mask_tensor,
    grid_to_layered_state,
    load_dmn_rule,
    phase_rollout,
    run_dmn_phase_on_layered,
    spatial_mask_tensor,
    _port_rect,
)
from casa.cli.train_dmn_nca import UpdateRule


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_gate_target(x: torch.Tensor, *, layout: LayeredChannelLayout, sn_rect) -> torch.Tensor:
    device = x.device
    h, w = x.shape[2], x.shape[3]
    tgt = torch.zeros_like(x)
    dig = x[0, layout.digest_slice]
    conf = dig.mean(dim=(1, 2))
    g = layout.n_gate
    for yi in range(h):
        for xi in range(w):
            if sn_rect.contains(xi, yi):
                for i in range(g):
                    src = i % layout.n_digest
                    tgt[0, layout.gate_slice.start + i, yi, xi] = conf[src]
    return tgt


def main() -> None:
    p = argparse.ArgumentParser(description="Train gate phase on layered field")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--dmn-model", type=Path, required=True)
    p.add_argument("--digest-model", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--gate-steps", type=int, default=12)
    p.add_argument("--digest-steps", type=int, default=16)
    p.add_argument("--epochs", type=int, default=300)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--hidden", type=int, default=48)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout_json = _read_json(args.layout)
    from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid, tokens_for_bundle

    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    dmn_rect = _get_region_rect(layout_json, "dmn_ontology")
    sn_rect = _get_region_rect(layout_json, "sn_router")
    target_grid = mask_outside_region(full, dmn_rect)
    damaged = damage_region_patches(
        target_grid, dmn_rect, patch_w=10, patch_h=10, count=args.damage_patches, seed=args.seed
    )

    dmn_rule, token_ids, dm_c, field_layout = load_dmn_rule(args.dmn_model, device)

    dck = torch.load(args.digest_model, map_location="cpu")
    digest_rule = UpdateRule(channel_n=int(dck["channel_n"]), hidden=int(dck["hidden"])).to(device)
    digest_rule.load_state_dict(dck["state_dict"])
    digest_rule.eval()

    port_rect = _port_rect(layout_json, "p1_dmn_to_sn")
    m_port = spatial_mask_tensor(port_rect, h=64, w=64, device=device)
    m_sn = spatial_mask_tensor(sn_rect, h=64, w=64, device=device)
    dig_mask = channel_mask_tensor(field_layout, "digest", device)
    gate_mask = channel_mask_tensor(field_layout, "gate", device)

    gate_rule = UpdateRule(channel_n=field_layout.channel_n, hidden=args.hidden).to(device)
    opt = torch.optim.Adam(gate_rule.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        x = grid_to_layered_state(damaged, token_ids, field_layout, device)
        with torch.no_grad():
            x = run_dmn_phase_on_layered(
                x, dmn_rule, field_layout=field_layout, dm_channel_n=dm_c, dmn_rect=dmn_rect, steps=48
            )
            x = phase_rollout(
                digest_rule, x, steps=args.digest_steps, channel_mask=dig_mask, spatial_mask=m_port, fire_rate=1.0
            )
            gate_tgt = build_gate_target(x, layout=field_layout, sn_rect=sn_rect)
        pred = phase_rollout(
            gate_rule, x, steps=args.gate_steps, channel_mask=gate_mask, spatial_mask=m_sn, fire_rate=0.5
        )
        loss = nn.functional.mse_loss(pred[:, field_layout.gate_slice], gate_tgt[:, field_layout.gate_slice])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % 50 == 0 or epoch == args.epochs - 1:
            print(f"epoch {epoch:4d} gate_loss={loss.item():.6f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "schema_version": 1,
            "role": "gate",
            "channel_n": field_layout.channel_n,
            "token_ids": token_ids,
            "gate_steps": args.gate_steps,
            "dmn_model": str(args.dmn_model),
            "digest_model": str(args.digest_model),
            "state_dict": gate_rule.state_dict(),
            "hidden": args.hidden,
        },
        args.out,
    )
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
