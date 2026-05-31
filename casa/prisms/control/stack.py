#!/usr/bin/env python3
"""Control lattice stack v0: DMN / SN / FPN / CEN as separate 32×32 grids."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.config_io import load_config
from casa.prisms.shared.lattice_names_v1 import (  # type: ignore
    CONTROL_ATTENTION,
    CONTROL_DMN,
    CONTROL_EXECUTIVE,
    CONTROL_PREDICT,
    CONTROL_SALIENCE,
    CONTROL_VALUE,
    CONTROL_WORKING_MEMORY,
)
from casa.prisms.memory.stack import _place_token, decode_lattice, encode_lattice

DEFAULT_STACK = Path("design/control-lattice-stack.json")


def load_control_stack(path: Path | None = None) -> dict:
    p = path or DEFAULT_STACK
    return load_config(p)


def lattice_meta(stack: dict, lattice_id: str) -> dict:
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lattice_id:
            return lat
    raise KeyError(lattice_id)


def empty_control_lattice(lat: dict) -> dict:
    size = lat.get("size") or {}
    w = int(size.get("width") or 32)
    h = int(size.get("height") or 32)
    return {
        "z_ctrl": int(lat.get("z_ctrl") or 0),
        "width": w,
        "height": h,
        "cells": [[] for _ in range(w * h)],
        "concept_prefix": str(lat.get("concept_prefix") or ""),
        "subsystem": "control",
    }


def _seed_sn_tokens(grid: Grid, *, copies: int) -> Grid:
    for tok in ("G:mode.probe", "G:mode.execute", "P:p1_dmn_to_sn", "port.digest.forward"):
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
    return grid


def _seed_fpn_tokens(grid: Grid, *, copies: int, mode: str = "explore", goal: str = "") -> Grid:
    grid = _place_token(grid, f"wm.mode.{mode}", f"wm.mode.{mode}", copies=copies, radius=5)
    if goal:
        g = goal.strip()[:48]
        grid = _place_token(grid, f"wm.goal.{g}", f"wm.goal.{g}", copies=max(2, copies // 2), radius=4)
    grid = _place_token(grid, "P:p2a_sn_to_fpn", "P:p2a_sn_to_fpn", copies=2, radius=3)
    grid = _place_token(grid, "P:p5_fpn_to_sn", "P:p5_fpn_to_sn", copies=2, radius=3)
    return grid


def _seed_predict_tokens(grid: Grid, *, copies: int) -> Grid:
    for tok in ("predict.rollout.v0", "P:p8_predict_to_sn", "port.surprise.forward"):
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
    return grid


def _seed_dan_tokens(grid: Grid, *, copies: int) -> Grid:
    for tok in ("dan.spotlight.goal", "P:p6_fpn_to_dan", "P:p7_dan_to_dmn", "port.mask.forward"):
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
    return grid


def _seed_value_tokens(grid: Grid, *, copies: int) -> Grid:
    for tok in ("value.priority.high", "P:p9_value_to_sn", "port.value.forward"):
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
    return grid


def _seed_cen_tokens(grid: Grid, *, copies: int) -> Grid:
    for tok in ("task.intent.explain", "task.action.navigate", "P:p2b_fpn_to_cen", "P:p3_cen_to_dmn", "P:p4_cen_to_outcome"):
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
    return grid


def encode_control_stack(
    bundle: dict,
    stack: dict | None = None,
    *,
    copies: int = 5,
    wm_mode: str = "explore",
    wm_goal: str = "",
) -> dict[str, dict]:
    """Imprint bundle + control seed tokens per lattice_id."""
    stack = stack or load_control_stack()
    claims = bundle.get("claims") or []
    edges = (bundle.get("graph") or {}).get("edges") or []
    out: dict[str, dict] = {}

    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        w = int((lat.get("size") or {}).get("width") or 32)
        h = int((lat.get("size") or {}).get("height") or 32)
        prefix = str(lat.get("concept_prefix") or "")

        if lid == CONTROL_DMN:
            grid_dict = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix="")
        elif lid == CONTROL_SALIENCE:
            sn_claims = [c for c in claims if str(c.get("concept_id", "")).startswith(("salience.", "gate."))]
            grid_dict = encode_lattice(sn_claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_sn_tokens(g, copies=copies)
            grid_dict["cells"] = g.cells
        elif lid == CONTROL_WORKING_MEMORY:
            wm_claims = [c for c in claims if str(c.get("concept_id", "")).startswith("wm.")]
            grid_dict = encode_lattice(wm_claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_fpn_tokens(g, copies=copies, mode=wm_mode, goal=wm_goal)
            grid_dict["cells"] = g.cells
        elif lid == CONTROL_EXECUTIVE:
            cen_claims = [c for c in claims if str(c.get("concept_id", "")).startswith("task.")]
            grid_dict = encode_lattice(cen_claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_cen_tokens(g, copies=copies)
            grid_dict["cells"] = g.cells
        elif lid == CONTROL_PREDICT:
            grid_dict = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_predict_tokens(g, copies=copies)
            grid_dict["cells"] = g.cells
        elif lid == CONTROL_ATTENTION:
            grid_dict = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_dan_tokens(g, copies=copies)
            grid_dict["cells"] = g.cells
        elif lid == CONTROL_VALUE:
            grid_dict = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
            g = Grid(width=w, height=h, cells=[list(x) for x in grid_dict["cells"]])
            g = _seed_value_tokens(g, copies=copies)
            grid_dict["cells"] = g.cells
        else:
            grid_dict = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)

        out[lid] = {
            "z_ctrl": int(lat.get("z_ctrl") or 0),
            "width": w,
            "height": h,
            "cells": grid_dict["cells"],
            "concept_prefix": prefix,
            "subsystem": "control",
        }

    apply_control_bridges(out, stack)
    return out


def apply_control_bridges(lattices: dict[str, dict], stack: dict | None = None) -> dict[str, Any]:
    """Stamp port.* tokens on bridge target lattices (spatial v0)."""
    stack = stack or load_control_stack()
    stamped: list[str] = []
    for br in stack.get("control_bridges") or []:
        tid = str(br.get("to") or "")
        if tid not in lattices:
            continue
        lat = lattices[tid]
        w, h = int(lat["width"]), int(lat["height"])
        g = Grid(width=w, height=h, cells=[list(x) for x in lat["cells"]])
        pid = str(br.get("id") or "bridge")
        tok = f"Z:bridge|{pid}|{br.get('kind') or 'port'}"
        g = _place_token(g, tok, tok, copies=2, radius=3)
        lat["cells"] = g.cells
        stamped.append(pid)
    return {"stamped_bridges": stamped, "count": len(stamped)}


def crop_layout_region_to_lattice(
    grid: dict,
    rect: dict,
    *,
    out_w: int = 32,
    out_h: int = 32,
) -> dict:
    """Copy tokens from layout rect on 64² into smaller lattice (top-left crop)."""
    gw = int(grid.get("width") or 64)
    cells = grid.get("cells") or []
    x0, y0 = int(rect["x0"]), int(rect["y0"])
    x1, y1 = int(rect["x1"]), int(rect["y1"])
    out_cells: list[list[str]] = [[] for _ in range(out_w * out_h)]
    for y in range(y0, min(y1 + 1, y0 + out_h)):
        for x in range(x0, min(x1 + 1, x0 + out_w)):
            if x >= gw or y >= gw:
                continue
            idx = y * gw + x
            if idx >= len(cells):
                continue
            ox, oy = x - x0, y - y0
            if ox < out_w and oy < out_h:
                out_cells[oy * out_w + ox] = list(cells[idx])
    return {"width": out_w, "height": out_h, "cells": out_cells}


def migrate_legacy_grid_to_control(
    grid: dict,
    layout: dict,
    stack: dict | None = None,
) -> dict[str, dict]:
    """layout.v0 regions → control lattices (fallback when no bundle)."""
    stack = stack or load_control_stack()
    region_map = {
        CONTROL_DMN: "dmn_ontology",
        CONTROL_SALIENCE: "sn_router",
        CONTROL_EXECUTIVE: "cen_planner",
    }
    out: dict[str, dict] = {}
    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        w = int((lat.get("size") or {}).get("width") or 32)
        h = int((lat.get("size") or {}).get("height") or 32)
        if lid == CONTROL_WORKING_MEMORY:
            base = empty_control_lattice(lat)
            g = Grid(width=w, height=h, cells=[[] for _ in range(w * h)])
            g = _seed_fpn_tokens(g, copies=4)
            base["cells"] = g.cells
            out[lid] = base
            continue
        rid = region_map.get(lid)
        if not rid:
            out[lid] = empty_control_lattice(lat)
            continue
        rect = None
        for reg in layout.get("regions") or []:
            if reg.get("id") == rid:
                rect = reg.get("rect")
                break
        if not rect:
            out[lid] = empty_control_lattice(lat)
            continue
        cropped = crop_layout_region_to_lattice(grid, rect, out_w=w, out_h=h)
        out[lid] = {
            "z_ctrl": int(lat.get("z_ctrl") or 0),
            "width": w,
            "height": h,
            "cells": cropped["cells"],
            "concept_prefix": str(lat.get("concept_prefix") or ""),
            "subsystem": "control",
            "migrated_from": rid,
        }
    apply_control_bridges(out, stack)
    return out


def decode_control_dmn(state: dict, *, min_votes: int = 1) -> dict:
    from casa.prisms.control.cylinders import control_lattices, has_control_stack  # type: ignore

    if not has_control_stack(state):
        raise ValueError("no control stack")
    lattices = control_lattices(state)
    lat = lattices[CONTROL_DMN]
    decoded = decode_lattice(lat, min_votes=min_votes)
    vote: dict[str, int] = {}
    for cell in lat.get("cells") or []:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1
    decoded["present_token_list"] = sorted([t for t, v in vote.items() if v >= min_votes])
    decoded["lattice_id"] = CONTROL_DMN
    return decoded
