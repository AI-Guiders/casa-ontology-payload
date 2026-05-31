#!/usr/bin/env python3
"""VK layout tables on field (L0_vk_map) — full keyboard compose v1."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import json
from pathlib import Path
from typing import Any, Literal

from codec_grid_v0 import Grid  # type: ignore
from grapheme_ingest_v0 import (  # type: ignore
    ingest_graphemes_batch,
)
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
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

L0_VK_MAP_ID = "L0_vk_map"  # legacy monolith (do not export in new core packs)
L0_VK_PHYSICAL_ID = "L0_vk_physical"
L0_LAYOUT_QWERTY_ID = "L0_layout_qwerty_us"
L0_LAYOUT_JCUKEN_ID = "L0_layout_jcuken_ru"
L0_PUNCT_LATN_ID = "L0_punct_latn"
L0_PUNCT_CYRL_ID = "L0_punct_cyrl"
VK_PHYSICAL_PREFIX = "vk.physical."
LAYOUT_REL_PREFIX = "layout."
LAYOUT_CONCEPT_PREFIX = "layout."
PUNCT_LATN_PREFIX = "punct.latn."
PUNCT_CYRL_PREFIX = "punct.cyrl."
OUTPUT_PREFIX = "output."
KEYBOARD_CORE_KIND = "core_ltm_keyboard_layouts_v1"
_LAYOUTS_DIR = Path(__file__).resolve().parent.parent / "design" / "keyboard-layouts"
_LAYOUT_FILES = {
    "qwerty_us": "qwerty-us.v0.toml",
    "jcuken_ru": "jcuken-ru.v0.toml",
}
LAYOUT_BASE_TO_LATTICE = {
    "qwerty_us": L0_LAYOUT_QWERTY_ID,
    "jcuken_ru": L0_LAYOUT_JCUKEN_ID,
}
VK_COMPOSE_LATTICE_IDS = (L0_LAYOUT_QWERTY_ID, L0_LAYOUT_JCUKEN_ID, L0_VK_MAP_ID)
VK_CORE_LATTICE_IDS = (
    L0_VK_PHYSICAL_ID,
    L0_LAYOUT_QWERTY_ID,
    L0_LAYOUT_JCUKEN_ID,
    L0_PUNCT_LATN_ID,
    L0_PUNCT_CYRL_ID,
)
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
    from config_io_v0 import load_config, resolve_config_path  # type: ignore

    base_id = layout_id.split(BASE_LAYOUT_SUFFIX)[0] if BASE_LAYOUT_SUFFIX in layout_id else layout_id
    name = _LAYOUT_FILES.get(base_id)
    if not name:
        raise KeyError(f"unknown layout_id: {layout_id!r}")
    config_path = _LAYOUTS_DIR / name
    json_path = config_path.with_suffix(".json")
    toml_path = config_path if config_path.suffix.lower() == ".toml" else config_path.with_suffix(".toml")
    if json_path.is_file():
        doc = json.loads(json_path.read_text(encoding="utf-8"))
    elif toml_path.is_file():
        doc = load_config(toml_path)
    else:
        doc = load_config(resolve_config_path(_LAYOUTS_DIR / name))
    doc.setdefault("locale", "ru" if base_id == "jcuken_ru" else "en")
    doc.setdefault("lang_concept", "lang.ru" if base_id == "jcuken_ru" else "lang.en")
    doc.setdefault(
        "alphabet_lattice",
        "L0_grapheme_cyrl" if base_id == "jcuken_ru" else "L0_grapheme_latn",
    )
    doc.setdefault(
        "punct_lattice",
        "L0_punct_cyrl" if base_id == "jcuken_ru" else "L0_punct_latn",
    )
    return doc


def layout_concept_id(base_layout_id: str) -> str:
    return f"{LAYOUT_CONCEPT_PREFIX}{base_layout_id}"


def punct_prefix_for_script(script: str) -> str:
    return PUNCT_CYRL_PREFIX if script == "cyrl" else PUNCT_LATN_PREFIX


def punct_concept_for_char(ch: str, script: str) -> str:
    return f"{punct_prefix_for_script(script)}{ch}"


def is_punctuation_char(ch: str) -> bool:
    return len(ch) == 1 and not ch.isalnum()


def punct_chars_for_layouts(layout_ids: list[str]) -> tuple[list[str], list[str]]:
    """Collect punctuation per layout locale (not grapheme script — shared ASCII punct is layout-scoped)."""
    latn: set[str] = set()
    cyrl: set[str] = set()
    for base_id in layout_ids:
        bucket = cyrl if base_id == "jcuken_ru" else latn
        for _layout_id, _key, ch, _ in iter_layout_maps([base_id]):
            if ch and is_punctuation_char(ch):
                bucket.add(ch)
    return sorted(latn), sorted(cyrl)


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


def build_vk_physical_lattice(*, width: int = 48, height: int = 48) -> dict[str, Any]:
    """Physical keys + modifiers/actions/zones (no layout→grapheme edges)."""
    grid = Grid.empty(width=width, height=height)
    seen_keys: set[str] = set()
    role_edges = 0
    zone_edges = 0
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
    lat["kind"] = KEYBOARD_CORE_KIND
    lat["role"] = "physical_catalog"
    lat["role_edge_count"] = role_edges
    lat["zone_edge_count"] = zone_edges
    lat["physical_key_count"] = len(seen_keys)
    return lat


def build_layout_lattice(
    base_layout_id: str,
    *,
    width: int = 32,
    height: int = 32,
) -> dict[str, Any]:
    """One full layout (base+shift layers) → grapheme/output edges + locale/alphabet links."""
    doc = load_layout_json(base_layout_id)
    grid = Grid.empty(width=width, height=height)
    seen_keys: set[str] = set()
    edge_count = 0
    for layout_id, key_id, char, shift in iter_layout_maps([base_layout_id]):
        _ensure_vk_concept(grid, key_id, seen_keys, copies=1)
        dst = dst_for_char(char, shift=shift)
        tok = edge_token(key_id, layout_id, dst)
        _place_token(grid, tok, tok, copies=2, radius=3)
        edge_count += 1
    lc = layout_concept_id(base_layout_id)
    _place_token(grid, lc, f"C:{lc}", copies=3, radius=5)
    lang = str(doc.get("lang_concept") or "")
    alphabet = str(doc.get("alphabet_lattice") or "")
    punct_lat = str(doc.get("punct_lattice") or "")
    locale = str(doc.get("locale") or "")
    if lang:
        _place_token(grid, meta_edge_token(lc, "locale", lang), meta_edge_token(lc, "locale", lang), copies=2, radius=4)
    if alphabet:
        _place_token(
            grid,
            meta_edge_token(lc, "alphabet_lattice", alphabet),
            meta_edge_token(lc, "alphabet_lattice", alphabet),
            copies=2,
            radius=4,
        )
    if punct_lat:
        _place_token(
            grid,
            meta_edge_token(lc, "punct_lattice", punct_lat),
            meta_edge_token(lc, "punct_lattice", punct_lat),
            copies=2,
            radius=4,
        )
    if locale:
        _place_token(grid, meta_edge_token(lc, "iso_locale", locale), meta_edge_token(lc, "iso_locale", locale), copies=1, radius=3)
    lat = _grid_to_dict(grid)
    lat["z_level"] = 0
    lat["concept_prefix"] = LAYOUT_CONCEPT_PREFIX
    lat["immutable"] = True
    lat["kind"] = KEYBOARD_CORE_KIND
    lat["layout_id"] = base_layout_id
    lat["locale"] = locale
    lat["lang_concept"] = lang
    lat["alphabet_lattice"] = alphabet
    lat["punct_lattice"] = punct_lat
    lat["edge_count"] = edge_count
    lat["physical_key_count"] = len(seen_keys)
    return lat


def build_punct_lattice(script: str, chars: list[str], *, width: int = 32, height: int = 32) -> dict[str, Any]:
    """Punctuation/symbol glyphs + realizes→grapheme.* edges."""
    from grapheme_ingest_v0 import l0_lattice_id  # type: ignore

    grid = Grid.empty(width=width, height=height)
    alphabet_lattice = l0_lattice_id("cyrl" if script == "cyrl" else "latn")
    for ch in chars:
        pc = punct_concept_for_char(ch, script)
        gc, _ = grapheme_concept_for_char(ch)
        _place_token(grid, pc, f"C:{pc}", copies=3, radius=4)
        tok = meta_edge_token(pc, "realizes", gc)
        _place_token(grid, tok, tok, copies=2, radius=3)
        tok2 = meta_edge_token(pc, "alphabet_lattice", alphabet_lattice)
        _place_token(grid, tok2, tok2, copies=1, radius=3)
    lat = _grid_to_dict(grid)
    lat["z_level"] = 0
    lat["concept_prefix"] = punct_prefix_for_script(script)
    lat["immutable"] = True
    lat["kind"] = KEYBOARD_CORE_KIND
    lat["script"] = script
    lat["glyph_count"] = len(chars)
    lat["alphabet_lattice"] = alphabet_lattice
    return lat


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
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    idx: dict[tuple[str, str], str] = {}
    for lid in VK_COMPOSE_LATTICE_IDS:
        lat = lattices.get(lid)
        if lat:
            idx.update(compose_index_from_lattice(lat))
    return idx or None


def role_index_from_state(state: dict) -> dict[str, str]:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    for lid in (L0_VK_PHYSICAL_ID, L0_VK_MAP_ID):
        lat = lattices.get(lid)
        if lat:
            r = role_index_from_lattice(lat)
            if r:
                return r
    return {}


def imprint_split_keyboard_on_field(
    state: dict,
    *,
    layout_ids: list[str] | None = None,
    ensure_graphemes: bool = True,
) -> dict[str, Any]:
    """Immutable listen: physical + per-layout + punct; links lang↔alphabet."""
    state = ensure_prisms(state)
    ids = layout_ids or list(_LAYOUT_FILES.keys())
    grapheme_rep: dict[str, Any] = {}
    if ensure_graphemes:
        latn, cyrl = unique_output_chars(ids)
        if latn:
            grapheme_rep["latn"] = ingest_graphemes_batch(state, latn, "latn", copies=3)
        if cyrl:
            grapheme_rep["cyrl"] = ingest_graphemes_batch(state, cyrl, "cyrl", copies=3)
    lattices = memory_lattices(state)
    lattices[L0_VK_PHYSICAL_ID] = build_vk_physical_lattice()
    for base_id in ids:
        lid = LAYOUT_BASE_TO_LATTICE[base_id]
        lattices[lid] = build_layout_lattice(base_id)
    latn_p, cyrl_p = punct_chars_for_layouts(ids)
    lattices[L0_PUNCT_LATN_ID] = build_punct_lattice("latn", latn_p)
    lattices[L0_PUNCT_CYRL_ID] = build_punct_lattice("cyrl", cyrl_p)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["field_version"] = int(state.get("field_version") or 0) + 1
    idx = compose_index_from_state(state) or {}
    return {
        "lattice_ids": list(VK_CORE_LATTICE_IDS),
        "mapping_count": len(idx),
        "layout_ids": ids,
        "graphemes": grapheme_rep,
        "punct_latn_n": len(latn_p),
        "punct_cyrl_n": len(cyrl_p),
        "immutable": True,
        "decode_mode": "compose",
        "verify": verify_keyboard_core_on_field(state),
    }


def verify_keyboard_core_on_field(state: dict) -> dict[str, Any]:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    idx = compose_index_from_state(state) or {}
    missing_lattices = [lid for lid in VK_CORE_LATTICE_IDS if lid not in lattices]
    qwerty_ok = L0_LAYOUT_QWERTY_ID in lattices and sum(
        1 for k in idx if str(k[0]).startswith("qwerty_us")
    ) >= 40
    jcuken_ok = L0_LAYOUT_JCUKEN_ID in lattices and sum(
        1 for k in idx if str(k[0]).startswith("jcuken_ru")
    ) >= 40
    return {
        "missing_lattices": missing_lattices,
        "mapping_count": len(idx),
        "qwerty_ok": qwerty_ok,
        "jcuken_ok": jcuken_ok,
        "physical_ok": L0_VK_PHYSICAL_ID in lattices,
        "punct_latn_ok": L0_PUNCT_LATN_ID in lattices,
        "punct_cyrl_ok": bool(lattices.get(L0_PUNCT_CYRL_ID, {}).get("glyph_count")),
        "pass": not missing_lattices and qwerty_ok and jcuken_ok,
    }


def imprint_vk_layouts_on_field(
    state: dict,
    *,
    layout_ids: list[str] | None = None,
    ensure_graphemes: bool = True,
    replace: bool = True,
) -> dict[str, Any]:
    """Listen path: split immutable keyboard lattices (physical + layouts + punct)."""
    _ = replace
    return imprint_split_keyboard_on_field(state, layout_ids=layout_ids, ensure_graphemes=ensure_graphemes)


def ensure_vk_compose_index(state: dict) -> dict[tuple[str, str], str]:
    idx = compose_index_from_state(state)
    if idx:
        return idx
    imprint_split_keyboard_on_field(state)
    return compose_index_from_state(state) or {}


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
