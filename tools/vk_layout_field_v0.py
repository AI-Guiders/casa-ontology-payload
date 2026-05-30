#!/usr/bin/env python3
"""VK layout tables on field (L0_vk_map) — full keyboard compose v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from codec_grid_v0 import Grid  # type: ignore
from grapheme_ingest_v0 import (  # type: ignore
    ingest_graphemes_batch,
)
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from sss_stack_v0 import _grid_to_dict, _place_token, decode_lattice  # type: ignore
from vk_grapheme_v0 import char_from_grapheme_concept, grapheme_concept_for_char  # type: ignore
from vk_keyboard_v0 import (  # type: ignore
    action_concept,
    action_key_ids,
    all_catalog_key_ids,
    device_concept_id,
    layout_layer_id,
    load_keyboard_catalog,
    modifier_concept,
    modifier_key_ids,
    zone_for_key,
)

L0_VK_MAP_ID = "L0_vk_map"
VK_PHYSICAL_PREFIX = "vk.physical."
LAYOUT_REL_PREFIX = "layout."
OUTPUT_PREFIX = "output."
_LAYOUTS_DIR = Path(__file__).resolve().parent.parent / "design" / "keyboard-layouts"
_LAYOUT_FILES = {
    "qwerty_us": "qwerty-us.v0.json",
    "jcuken_ru": "jcuken-ru.v0.json",
}
DecodeMode = Literal["compose", "flat", "json"]
BASE_LAYOUT_SUFFIX = ".shift"


def vk_physical_concept(key_id: str) -> str:
    return f"{VK_PHYSICAL_PREFIX}{key_id}"


def layout_rel(layout_id: str) -> str:
    return f"{LAYOUT_REL_PREFIX}{layout_id}"


def dst_for_char(ch: str, *, shift: bool = False) -> str:
    if shift or (len(ch) == 1 and ch.isalpha() and ch.isupper()):
        return f"{OUTPUT_PREFIX}{ch}"
    g_cid, _ = grapheme_concept_for_char(ch)
    return g_cid


def char_from_edge_dst(dst: str) -> str | None:
    if dst.startswith(OUTPUT_PREFIX):
        payload = dst[len(OUTPUT_PREFIX) :]
        return payload if payload else None
    return char_from_grapheme_concept(dst)


def edge_token(key_id: str, layout_id: str, dst: str) -> str:
    return f"E:{vk_physical_concept(key_id)}|{layout_rel(layout_id)}|{dst}"


def role_edge_token(key_id: str, role: str, concept_id: str) -> str:
    return f"E:{vk_physical_concept(key_id)}|{role}|{concept_id}"


def meta_edge_token(src: str, rel: str, dst: str) -> str:
    return f"E:{src}|{rel}|{dst}"


def parse_grapheme_edge(edge: str) -> tuple[str, str, str] | None:
    parts = (edge or "").split("|", 2)
    if len(parts) != 3:
        return None
    src, rel, dst = parts
    if not src.startswith(VK_PHYSICAL_PREFIX) or not rel.startswith(LAYOUT_REL_PREFIX):
        return None
    key_id = src[len(VK_PHYSICAL_PREFIX) :]
    layout_id = rel[len(LAYOUT_REL_PREFIX) :]
    if not key_id or not layout_id:
        return None
    return layout_id, key_id, dst


def parse_role_edge(edge: str) -> tuple[str, str, str] | None:
    parts = (edge or "").split("|", 2)
    if len(parts) != 3:
        return None
    src, rel, dst = parts
    if not src.startswith(VK_PHYSICAL_PREFIX) or rel in ("layout",) or rel.startswith(LAYOUT_REL_PREFIX):
        return None
    key_id = src[len(VK_PHYSICAL_PREFIX) :]
    if not key_id or not rel or not dst:
        return None
    return key_id, rel, dst


def is_base_layout_id(layout_id: str) -> bool:
    return BASE_LAYOUT_SUFFIX not in layout_id


def load_layout_json(layout_id: str) -> dict[str, Any]:
    base_id = layout_id.split(BASE_LAYOUT_SUFFIX)[0] if BASE_LAYOUT_SUFFIX in layout_id else layout_id
    name = _LAYOUT_FILES.get(base_id)
    if not name:
        raise KeyError(f"unknown layout_id: {layout_id!r}")
    return json.loads((_LAYOUTS_DIR / name).read_text(encoding="utf-8"))


def iter_layout_maps(layout_ids: list[str] | None = None) -> list[tuple[str, str, str, bool]]:
    ids = layout_ids or list(_LAYOUT_FILES.keys())
    rows: list[tuple[str, str, str, bool]] = []
    for layout_id in ids:
        doc = load_layout_json(layout_id)
        for key_id, char in (doc.get("map") or {}).items():
            if char:
                rows.append((layout_id, str(key_id), str(char), False))
        for key_id, char in (doc.get("map_shift") or {}).items():
            if char:
                rows.append((layout_layer_id(layout_id, shift=True), str(key_id), str(char), True))
    return rows


def unique_output_chars(layout_ids: list[str] | None = None) -> tuple[list[str], list[str]]:
    latn: set[str] = set()
    cyrl: set[str] = set()
    for _, _, ch, _ in iter_layout_maps(layout_ids):
        try:
            _, script = grapheme_concept_for_char(ch.lower() if ch.isalpha() else ch)
        except ValueError:
            _, script = grapheme_concept_for_char(ch)
        if script == "cyrl":
            cyrl.add(ch.lower() if ch.isalpha() else ch)
        else:
            latn.add(ch.lower() if ch.isalpha() else ch)
    return sorted(latn), sorted(cyrl)


def _ensure_vk_concept(grid: Grid, key_id: str, seen: set[str], *, copies: int = 2) -> None:
    if key_id in seen:
        return
    vk_cid = vk_physical_concept(key_id)
    _place_token(grid, vk_cid, f"C:{vk_cid}", copies=copies, radius=4)
    seen.add(key_id)


def build_vk_lattice(
    *,
    layout_ids: list[str] | None = None,
    width: int = 48,
    height: int = 48,
    include_catalog: bool = True,
) -> dict[str, Any]:
    grid = Grid.empty(width=width, height=height)
    seen_keys: set[str] = set()
    edge_count = 0
    role_edges = 0
    zone_edges = 0

    for layout_id, key_id, char, shift in iter_layout_maps(layout_ids):
        _ensure_vk_concept(grid, key_id, seen_keys)
        dst = dst_for_char(char, shift=shift)
        tok = edge_token(key_id, layout_id, dst)
        _place_token(grid, tok, tok, copies=2, radius=3)
        edge_count += 1

    if include_catalog:
        dev = device_concept_id()
        _place_token(grid, dev, f"C:{dev}", copies=3, radius=5)
        for key_id in all_catalog_key_ids():
            _ensure_vk_concept(grid, key_id, seen_keys)
            mod = modifier_concept(key_id)
            if mod:
                tok = role_edge_token(key_id, "role", mod)
                _place_token(grid, tok, tok, copies=2, radius=3)
                role_edges += 1
            act = action_concept(key_id)
            if act:
                _place_token(grid, act, f"C:{act}", copies=2, radius=4)
                tok = role_edge_token(key_id, "role", act)
                _place_token(grid, tok, tok, copies=2, radius=3)
                role_edges += 1
            zone = zone_for_key(key_id)
            if zone:
                _place_token(grid, zone, f"C:{zone}", copies=2, radius=4)
                tok = meta_edge_token(vk_physical_concept(key_id), "zone", zone)
                _place_token(grid, tok, tok, copies=2, radius=3)
                zone_edges += 1
                tok = meta_edge_token(zone, "part_of", dev)
                _place_token(grid, tok, tok, copies=1, radius=3)
                zone_edges += 1

        for mod_cid in set(load_keyboard_catalog().get("modifiers") or {}.values()):
            _place_token(grid, mod_cid, f"C:{mod_cid}", copies=2, radius=4)

    lat = _grid_to_dict(grid)
    lat["z_level"] = 0
    lat["concept_prefix"] = "vk."
    lat["immutable"] = True
    lat["kind"] = "vk_keyboard_compose_v1"
    lat["edge_count"] = edge_count
    lat["role_edge_count"] = role_edges
    lat["zone_edge_count"] = zone_edges
    lat["physical_key_count"] = len(seen_keys)
    return lat


def compose_index_from_lattice(lattice: dict[str, Any]) -> dict[tuple[str, str], str]:
    dec = decode_lattice(lattice, min_votes=1)
    idx: dict[tuple[str, str], str] = {}
    for edge in dec.get("edges") or []:
        parsed = parse_grapheme_edge(str(edge))
        if not parsed:
            continue
        layout_id, key_id, dst = parsed
        ch = char_from_edge_dst(dst)
        if ch:
            idx[(layout_id, key_id)] = ch
    return idx


def role_index_from_lattice(lattice: dict[str, Any]) -> dict[str, str]:
    dec = decode_lattice(lattice, min_votes=1)
    idx: dict[str, str] = {}
    for edge in dec.get("edges") or []:
        parsed = parse_role_edge(str(edge))
        if not parsed:
            continue
        key_id, _rel, concept_id = parsed
        idx[key_id] = concept_id
    return idx


def compose_index_from_state(state: dict) -> dict[tuple[str, str], str] | None:
    state = ensure_cylinders(state)
    lat = memory_lattices(state).get(L0_VK_MAP_ID)
    if not lat:
        return None
    idx = compose_index_from_lattice(lat)
    return idx or None


def imprint_vk_layouts_on_field(
    state: dict,
    *,
    layout_ids: list[str] | None = None,
    ensure_graphemes: bool = True,
    replace: bool = True,
) -> dict[str, Any]:
    """Listen path: layouts + keyboard catalog → L0_vk_map + L0_grapheme."""
    state = ensure_cylinders(state)
    _ = replace

    grapheme_rep: dict[str, Any] = {}
    if ensure_graphemes:
        latn, cyrl = unique_output_chars(layout_ids)
        if latn:
            grapheme_rep["latn"] = ingest_graphemes_batch(state, latn, "latn", copies=3)
        if cyrl:
            grapheme_rep["cyrl"] = ingest_graphemes_batch(state, cyrl, "cyrl", copies=3)

    lat = build_vk_lattice(layout_ids=layout_ids, include_catalog=True)
    lattices = memory_lattices(state)
    lattices[L0_VK_MAP_ID] = lat
    state["cylinders"]["cyl_memory"]["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    idx = compose_index_from_lattice(lat)
    base_layouts = sorted({k[0] for k in idx if is_base_layout_id(k[0])})
    return {
        "lattice_id": L0_VK_MAP_ID,
        "mapping_count": len(idx),
        "edge_count": int(lat.get("edge_count") or 0),
        "role_edge_count": int(lat.get("role_edge_count") or 0),
        "zone_edge_count": int(lat.get("zone_edge_count") or 0),
        "physical_key_count": int(lat.get("physical_key_count") or 0),
        "layout_ids": base_layouts,
        "graphemes": grapheme_rep,
        "immutable": True,
        "decode_mode": "compose",
        "keyboard_kind": lat.get("kind"),
    }


def ensure_vk_compose_index(state: dict) -> dict[tuple[str, str], str]:
    idx = compose_index_from_state(state)
    if idx:
        return idx
    imprint_vk_layouts_on_field(state)
    return compose_index_from_lattice(memory_lattices(state)[L0_VK_MAP_ID])


# Legacy flat-token index (v0 migration / oracle only)
VK_TOKEN_PREFIX = "vk:"


def parse_mapping_token(token: str) -> tuple[str, str, str] | None:
    if not token.startswith(VK_TOKEN_PREFIX):
        return None
    body = token[len(VK_TOKEN_PREFIX) :]
    parts = body.split(":", 2)
    if len(parts) != 3:
        return None
    layout_id, key_id, char = parts
    if not layout_id or not key_id:
        return None
    return layout_id, key_id, char


def flat_index_from_lattice(lattice: dict[str, Any]) -> dict[tuple[str, str], str]:
    idx: dict[tuple[str, str], str] = {}
    w = int(lattice.get("width") or 0)
    h = int(lattice.get("height") or 0)
    cells = lattice.get("cells") or []
    for yi in range(h):
        for xi in range(w):
            pos = yi * w + xi
            for token in cells[pos] if pos < len(cells) else []:
                parsed = parse_mapping_token(str(token))
                if parsed:
                    layout_id, key_id, char = parsed
                    idx[(layout_id, key_id)] = char
    return idx
