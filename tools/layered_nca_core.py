#!/usr/bin/env python3
"""
Layered CA on one field: phased rollout with regional + channel masks.

Analogy: piston through z-sections; same (x,y) buffer; rules change per phase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn

from layout_apply import Rect, _get_region_rect, _rect_from  # type: ignore
from train_dmn_nca import UpdateRule, nca_rollout_eval, perceive, sobel_kernels  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class LayeredChannelLayout:
    k_tokens: int
    n_digest: int = 8
    n_gate: int = 4
    n_hidden: int = 8

    @property
    def n_tok(self) -> int:
        return self.k_tokens

    @property
    def tok_slice(self) -> slice:
        return slice(0, self.k_tokens)

    @property
    def digest_slice(self) -> slice:
        a = self.k_tokens
        return slice(a, a + self.n_digest)

    @property
    def gate_slice(self) -> slice:
        a = self.k_tokens + self.n_digest
        return slice(a, a + self.n_gate)

    @property
    def hidden_slice(self) -> slice:
        a = self.k_tokens + self.n_digest + self.n_gate
        return slice(a, a + self.n_hidden)

    @property
    def channel_n(self) -> int:
        return self.k_tokens + self.n_digest + self.n_gate + self.n_hidden


def _port_rect(layout: dict, port_id: str) -> Rect:
    for p in layout.get("ports", []):
        if p.get("id") == port_id:
            return _rect_from(p["rect"])
    raise KeyError(port_id)


def spatial_mask_tensor(rect: Rect, *, h: int, w: int, device: torch.device) -> torch.Tensor:
    m = torch.zeros(h, w, device=device)
    for y in range(h):
        for x in range(w):
            if rect.contains(x, y):
                m[y, x] = 1.0
    return m.view(1, 1, h, w)


def channel_mask_tensor(layout: LayeredChannelLayout, group: str, device: torch.device) -> torch.Tensor:
    c = layout.channel_n
    m = torch.zeros(c, device=device)
    if group == "tok":
        m[layout.tok_slice] = 1.0
    elif group == "digest":
        m[layout.digest_slice] = 1.0
    elif group == "gate":
        m[layout.gate_slice] = 1.0
    elif group == "all_learned":
        m[layout.tok_slice] = 1.0
        m[layout.digest_slice] = 1.0
        m[layout.gate_slice] = 1.0
    else:
        raise ValueError(group)
    return m.view(1, c, 1, 1)


def phase_rollout(
    rule: UpdateRule,
    x: torch.Tensor,
    *,
    steps: int,
    channel_mask: torch.Tensor,
    spatial_mask: torch.Tensor,
    fire_rate: float = 1.0,
) -> torch.Tensor:
    device = x.device
    kx, ky = sobel_kernels(device)
    for _ in range(steps):
        p = perceive(x, kx, ky)
        dx = rule(p)
        if fire_rate < 1.0:
            dx = dx * (torch.rand_like(dx[:, :1]) + fire_rate).floor()
        dx = dx * channel_mask * spatial_mask
        x = (x + dx).clamp(0.0, 1.0)
    return x


def grid_to_layered_state(
    grid: dict,
    token_ids: list[str],
    layout: LayeredChannelLayout,
    device: torch.device,
) -> torch.Tensor:
    """Map grid cells into layered tensor using union token_ids (checkpoint vocab)."""
    w, h = int(grid["width"]), int(grid["height"])
    if layout.k_tokens != len(token_ids):
        raise ValueError("layout.k_tokens must match len(token_ids)")
    ch = layout.channel_n
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    x = torch.zeros(1, ch, h, w, device=device)
    for idx, cell in enumerate(grid["cells"]):
        y = idx // w
        xi = idx % w
        for t in cell:
            j = token_to_i.get(t)
            if j is not None:
                x[0, j, y, xi] = 1.0
    return x


def build_digest_target(
    target_tok: torch.Tensor,
    *,
    layout: LayeredChannelLayout,
    port_rect: Rect,
    h: int,
    w: int,
) -> torch.Tensor:
    """Pool DMN token activations -> digest channels on port cells."""
    device = target_tok.device
    tgt = torch.zeros(1, layout.channel_n, h, w, device=device)
    # global max over full grid per token channel
    pooled = target_tok[0, layout.tok_slice].amax(dim=(1, 2))  # [K]
    d = layout.n_digest
    k = pooled.shape[0]
    for i in range(min(d, k)):
        val = pooled[i]
        for y in range(h):
            for x in range(w):
                if port_rect.contains(x, y):
                    tgt[0, layout.digest_slice.start + i, y, x] = val
    return tgt


def gate_from_digest_step(x: torch.Tensor, *, layout: LayeredChannelLayout, sn_rect: Rect) -> torch.Tensor:
    """Deterministic z=gate: SN gate channels <- mean digest confidence."""
    device = x.device
    dig = x[0, layout.digest_slice]  # [D,H,W]
    conf = dig.mean(dim=(1, 2))  # [D]
    g = layout.n_gate
    for yi in range(x.shape[2]):
        for xi in range(x.shape[3]):
            if sn_rect.contains(xi, yi):
                for i in range(g):
                    src = i % layout.n_digest
                    x[0, layout.gate_slice.start + i, yi, xi] = conf[src].clamp(0.0, 1.0)
    return x


@dataclass
class PhaseCheckpoints:
    dmn: Path | None = None
    digest: Path | None = None


def load_dmn_rule(ckpt_path: Path, device: torch.device) -> tuple[UpdateRule, list[str], int, LayeredChannelLayout]:
    ckpt = torch.load(ckpt_path, map_location="cpu")
    token_ids = list(ckpt["token_ids"])
    k = len(token_ids)
    fl = ckpt.get("field_layout")
    if isinstance(fl, dict):
        layout = LayeredChannelLayout(
            k_tokens=int(fl.get("k_tokens", k)),
            n_digest=int(fl.get("n_digest", 8)),
            n_gate=int(fl.get("n_gate", 4)),
            n_hidden=int(fl.get("n_hidden", 8)),
        )
    else:
        layout = LayeredChannelLayout(k_tokens=k)
    dm_c = int(ckpt["channel_n"])
    rule = UpdateRule(channel_n=dm_c, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    return rule, token_ids, dm_c, layout


def run_dmn_phase_on_layered(
    x: torch.Tensor,
    dmn_rule: UpdateRule,
    *,
    field_layout: LayeredChannelLayout,
    dm_channel_n: int,
    dmn_rect: Rect,
    steps: int,
) -> torch.Tensor:
    """Run DMN checkpoint (K+hidden_dm channels) on layered buffer without touching digest/gate."""
    device = x.device
    k = field_layout.k_tokens
    h_dm = dm_channel_n - k
    h, w = x.shape[2], x.shape[3]
    sub = torch.zeros(1, dm_channel_n, h, w, device=device)
    sub[:, :k] = x[:, field_layout.tok_slice]
    if h_dm > 0:
        sub[:, k:] = x[:, field_layout.hidden_slice][:, :h_dm]
    m = spatial_mask_tensor(dmn_rect, h=h, w=w, device=device)
    tok_mask = torch.zeros(dm_channel_n, device=device)
    tok_mask[:k] = 1.0
    tok_mask = tok_mask.view(1, dm_channel_n, 1, 1)
    sub = phase_rollout(dmn_rule, sub, steps=steps, channel_mask=tok_mask, spatial_mask=m, fire_rate=1.0)
    x[:, field_layout.tok_slice] = sub[:, :k]
    if h_dm > 0:
        x[:, field_layout.hidden_slice][:, :h_dm] = sub[:, k:]
    return x


def run_piston_pipeline(
    x: torch.Tensor,
    *,
    field_layout: LayeredChannelLayout,
    layout_json: dict,
    dmn_rule: UpdateRule,
    dm_channel_n: int,
    digest_rule: UpdateRule | None = None,
    gate_rule: UpdateRule | None = None,
    dmn_steps: int = 48,
    digest_steps: int = 16,
    gate_steps: int = 12,
    run_gate: bool = True,
) -> torch.Tensor:
    device = x.device
    h, w = x.shape[2], x.shape[3]
    dmn_rect = _get_region_rect(layout_json, "dmn_ontology")
    port_rect = _port_rect(layout_json, "p1_dmn_to_sn")
    sn_rect = _get_region_rect(layout_json, "sn_router")
    m_port = spatial_mask_tensor(port_rect, h=h, w=w, device=device)

    x = run_dmn_phase_on_layered(
        x, dmn_rule, field_layout=field_layout, dm_channel_n=dm_channel_n, dmn_rect=dmn_rect, steps=dmn_steps
    )

    if digest_rule is not None:
        x = phase_rollout(
            digest_rule,
            x,
            steps=digest_steps,
            channel_mask=channel_mask_tensor(field_layout, "digest", device),
            spatial_mask=m_port,
            fire_rate=1.0,
        )

    if run_gate:
        if gate_rule is not None:
            m_sn = spatial_mask_tensor(sn_rect, h=h, w=w, device=device)
            x = phase_rollout(
                gate_rule,
                x,
                steps=gate_steps,
                channel_mask=channel_mask_tensor(field_layout, "gate", device),
                spatial_mask=m_sn,
                fire_rate=1.0,
            )
        else:
            x = gate_from_digest_step(x, layout=field_layout, sn_rect=sn_rect)
    return x
