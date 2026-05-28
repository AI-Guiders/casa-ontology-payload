#!/usr/bin/env python3
"""Spatial masks and module-local damage for (doc_path, section) parcels."""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass

from codec_grid_v3 import _section_key, tokens_for_bundle  # type: ignore
from layout_apply import Rect, damage_region_patches  # type: ignore


def section_slug(section: str, *, max_len: int = 40) -> str:
    """Filesystem-safe short id from section title."""
    s = section.strip().lower()
    s = re.sub(r"[^\w\-]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        h = hashlib.sha256(section.encode("utf-8")).hexdigest()[:8]
        return f"sec-{h}"
    if len(s) > max_len:
        h = hashlib.sha256(section.encode("utf-8")).hexdigest()[:6]
        return f"{s[: max_len - 7]}-{h}"
    return s


@dataclass(frozen=True)
class ModuleSpec:
    cluster: str
    bundle_name: str
    module_id: str
    doc_path: str
    section: str
    section_key: str

    @property
    def section_token(self) -> str:
        return f"S:{self.section_key}"


def enumerate_sections(bundle: dict) -> list[tuple[str, str]]:
    """Unique (doc_path, section) pairs from claims."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for c in bundle.get("claims", []):
        dp, sec = c.get("doc_path"), c.get("section")
        if not (dp and sec):
            continue
        sk = _section_key(str(dp), str(sec))
        if sk in seen:
            continue
        seen.add(sk)
        out.append((str(dp), str(sec)))
    return sorted(out, key=lambda x: x[1])


def module_tokens_for_section(
    bundle: dict,
    *,
    doc_path: str,
    section: str,
    concept_mode: str = "section",
) -> set[str]:
    """Tokens that belong to a section parcel (hub, concepts, doc node, incident edges)."""
    section_key = _section_key(doc_path, section)
    hub = f"S:{section_key}"
    doc_node = f"N:{doc_path}"

    toks = set(tokens_for_bundle(bundle, concept_mode=concept_mode))
    selected: set[str] = set()
    if hub in toks:
        selected.add(hub)
    if doc_node in toks:
        selected.add(doc_node)

    for c in bundle.get("claims", []):
        if str(c.get("doc_path") or "") != doc_path:
            continue
        if str(c.get("section") or "") != section:
            continue
        cid = c.get("concept_id")
        if cid:
            t = f"C:{cid}"
            if t in toks:
                selected.add(t)

    for t in toks:
        if not t.startswith("E:"):
            continue
        # E:src|rel|dst — include if src or dst is doc_path
        body = t[2:]
        parts = body.split("|", 2)
        if len(parts) != 3:
            continue
        src, _, dst = parts
        if src == doc_path or dst == doc_path:
            selected.add(t)

    return selected


def cell_indices_for_tokens(grid: dict, tokens: set[str]) -> set[int]:
    w = int(grid["width"])
    out: set[int] = set()
    for idx, cell in enumerate(grid["cells"]):
        if any(t in tokens for t in cell):
            out.add(idx)
    return out


def spatial_mask_from_cells(
    grid: dict,
    cell_indices: set[int],
    *,
    device,
) -> "torch.Tensor":
    import torch

    h, w = int(grid["height"]), int(grid["width"])
    m = torch.zeros(1, 1, h, w, device=device)
    for idx in cell_indices:
        y, x = idx // w, idx % w
        m[0, 0, y, x] = 1.0
    return m


def damage_module_patches(
    grid: dict,
    rect: Rect,
    module_cells: set[int],
    *,
    patch_w: int,
    patch_h: int,
    count: int,
    seed: int,
) -> tuple[dict, float]:
    """
    Clear patches whose anchor lies in module_cells (fallback: any overlap).
    Returns (damaged_grid, mean_fraction_of_patch_cells_in_module).
    """
    w = int(grid["width"])
    h = int(grid["height"])
    if not module_cells:
        return damage_region_patches(
            grid, rect, patch_w=patch_w, patch_h=patch_h, count=count, seed=seed
        ), 0.0

    cells = [list(x) for x in grid["cells"]]
    rng = random.Random(seed)
    patch_w = max(1, min(patch_w, rect.x1 - rect.x0 + 1, w))
    patch_h = max(1, min(patch_h, rect.y1 - rect.y0 + 1, h))

    overlaps: list[float] = []
    for _ in range(count):
        # Prefer patch anchor inside module
        module_list = sorted(module_cells)
        anchor_idx = module_list[rng.randrange(len(module_list))]
        ax, ay = anchor_idx % w, anchor_idx // w
        x0 = max(rect.x0, min(ax - patch_w // 2, rect.x1 - patch_w + 1))
        y0 = max(rect.y0, min(ay - patch_h // 2, rect.y1 - patch_h + 1))
        patch_cells: set[int] = set()
        for yy in range(y0, y0 + patch_h):
            for xx in range(x0, x0 + patch_w):
                if 0 <= xx < w and 0 <= yy < h:
                    patch_cells.add(yy * w + xx)
        if patch_cells:
            overlaps.append(len(patch_cells & module_cells) / len(patch_cells))
        for i in patch_cells:
            cells[i] = []

    out = dict(grid)
    out["cells"] = cells
    out["damage"] = {
        "type": "module_patches",
        "patch_w": patch_w,
        "patch_h": patch_h,
        "count": count,
        "seed": seed,
    }
    mean_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
    return out, mean_overlap
