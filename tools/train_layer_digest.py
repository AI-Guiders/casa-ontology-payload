#!/usr/bin/env python3
"""Train z=digest layer (full field) with frozen DMN repair checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn

from canonical import CANONICAL_CONCEPT_MODE, CANONICAL_THRESHOLD  # type: ignore
from layout_apply import _get_region_rect, damage_region_patches, mask_outside_region  # type: ignore
from layered_nca_core import (  # type: ignore
    LayeredChannelLayout,
    build_digest_target,
    grid_to_layered_state,
    load_dmn_rule,
    run_dmn_phase_on_layered,
    phase_rollout,
    channel_mask_tensor,
    spatial_mask_tensor,
    _port_rect,
)
from train_dmn_nca import UpdateRule  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Train digest phase on layered field")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--dmn-model", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--digest-steps", type=int, default=16)
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--out", type=Path, default=Path("lab/layered_out/digest_model.pt"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout_json = _read_json(args.layout)

    from codec_grid_v3 import encode_bundle_to_grid, tokens_for_bundle  # type: ignore

    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    dmn_rect = _get_region_rect(layout_json, "dmn_ontology")
    target_grid = mask_outside_region(full, dmn_rect)
    damaged = damage_region_patches(
        target_grid, dmn_rect, patch_w=10, patch_h=10, count=args.damage_patches, seed=args.seed
    )

    dmn_rule, token_ids, dm_c, field_layout = load_dmn_rule(args.dmn_model, device)

    tgt_state = grid_to_layered_state(target_grid, token_ids, field_layout, device)
    x = grid_to_layered_state(damaged, token_ids, field_layout, device)
    port_rect = _port_rect(layout_json, "p1_dmn_to_sn")
    digest_tgt = build_digest_target(
        tgt_state, layout=field_layout, port_rect=port_rect, h=64, w=64
    )

    # Freeze DMN path for target digest: repair then build target digest from repaired tok
    with torch.no_grad():
        x_rep = run_dmn_phase_on_layered(
            x.clone(), dmn_rule, field_layout=field_layout, dm_channel_n=dm_c, dmn_rect=dmn_rect, steps=48
        )
        digest_tgt = build_digest_target(x_rep, layout=field_layout, port_rect=port_rect, h=64, w=64)

    digest_rule = UpdateRule(channel_n=field_layout.channel_n, hidden=args.hidden).to(device)
    opt = torch.optim.Adam(digest_rule.parameters(), lr=args.lr)
    m_port = spatial_mask_tensor(port_rect, h=64, w=64, device=device)
    ch_mask = channel_mask_tensor(field_layout, "digest", device)

    for epoch in range(args.epochs):
        with torch.no_grad():
            x0 = run_dmn_phase_on_layered(
                x.clone(), dmn_rule, field_layout=field_layout, dm_channel_n=dm_c, dmn_rect=dmn_rect, steps=48
            )
        pred = phase_rollout(
            digest_rule, x0, steps=args.digest_steps, channel_mask=ch_mask, spatial_mask=m_port, fire_rate=0.5
        )
        loss = nn.functional.mse_loss(pred[:, field_layout.digest_slice], digest_tgt[:, field_layout.digest_slice])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % 50 == 0 or epoch == args.epochs - 1:
            print(f"epoch {epoch:4d} digest_loss={loss.item():.6f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "schema_version": 1,
            "role": "digest",
            "channel_n": field_layout.channel_n,
            "token_ids": token_ids,
            "field_layout": {
                "k_tokens": field_layout.k_tokens,
                "n_digest": field_layout.n_digest,
                "n_gate": field_layout.n_gate,
                "n_hidden": field_layout.n_hidden,
            },
            "hidden": args.hidden,
            "digest_steps": args.digest_steps,
            "dmn_model": str(args.dmn_model),
            "state_dict": digest_rule.state_dict(),
        },
        args.out,
    )
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
