#!/usr/bin/env python3
"""Decode PhysicalKeyEvent[] via field compose (vk → grapheme / action / shift layer)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from vk_keyboard_v0 import (  # type: ignore
    CAPS_LOCK_KEY,
    SHIFT_KEYS,
    action_concept,
    action_glyph,
    layout_layer_id,
    modifier_key_ids,
)
from vk_layout_field_v0 import (  # type: ignore
    _LAYOUT_FILES,
    compose_index_from_state,
    ensure_vk_compose_index,
    is_base_layout_id,
    load_layout_json,
    role_index_from_lattice,
)

Action = Literal["down", "up"]


class _ModifierState:
    __slots__ = ("shift", "caps_latched")

    def __init__(self) -> None:
        self.shift = 0
        self.caps_latched = False

    def apply(self, key_id: str, action: str) -> bool:
        if key_id not in modifier_key_ids():
            return False
        if key_id == CAPS_LOCK_KEY:
            if action == "down":
                self.caps_latched = not self.caps_latched
            return True
        if key_id in SHIFT_KEYS:
            if action == "down":
                self.shift += 1
            elif action == "up":
                self.shift = max(0, self.shift - 1)
        return True

    @property
    def shift_active(self) -> bool:
        return self.shift > 0 or self.caps_latched


@lru_cache(maxsize=8)
def _json_index() -> dict[tuple[str, str], str]:
    idx: dict[tuple[str, str], str] = {}
    for layout_id in _LAYOUT_FILES:
        doc = load_layout_json(layout_id)
        for key_id, char in (doc.get("map") or {}).items():
            if char:
                idx[(layout_id, str(key_id))] = str(char)
        for key_id, char in (doc.get("map_shift") or {}).items():
            if char:
                idx[(layout_layer_id(layout_id, shift=True), str(key_id))] = str(char)
    return idx


def resolve_decode_index(
    *,
    state: dict | None = None,
) -> tuple[dict[tuple[str, str], str], str]:
    if state is not None:
        state = ensure_prisms(state)
        compose = compose_index_from_state(state)
        if compose:
            return compose, "compose"
        lat = memory_lattices(state).get("L0_vk_map")
        if lat:
            from vk_layout_field_v0 import flat_index_from_lattice  # type: ignore

            flat = flat_index_from_lattice(lat)
            if flat:
                return flat, "flat_legacy"
    return _json_index(), "json"


def resolve_role_index(*, state: dict | None = None) -> dict[str, str]:
    if state is None:
        return {}
    state = ensure_prisms(state)
    from vk_layout_field_v0 import role_index_from_state  # type: ignore

    return role_index_from_state(state)


def list_layout_ids(*, state: dict | None = None) -> list[str]:
    idx, _ = resolve_decode_index(state=state)
    return sorted({layout for layout, _ in idx if is_base_layout_id(layout)})


def decode_events(
    events: list[dict[str, Any]],
    layout_id: str,
    *,
    vk_index: dict[tuple[str, str], str] | None = None,
    role_index: dict[str, str] | None = None,
    state: dict | None = None,
    actions: tuple[Action, ...] = ("down",),
) -> str:
    if vk_index is None:
        vk_index, _ = resolve_decode_index(state=state)
    if role_index is None:
        role_index = resolve_role_index(state=state)

    mods = _ModifierState()
    out: list[str] = []
    for ev in events:
        action = str(ev.get("action") or "down").lower()
        if action not in actions:
            continue
        key_id = str(ev.get("key_id") or "")
        if not key_id:
            continue
        if mods.apply(key_id, action):
            continue

        act_cid = action_concept(key_id) or role_index.get(key_id)
        if act_cid and act_cid.startswith("action."):
            glyph = action_glyph(act_cid)
            if glyph:
                out.append(glyph)
            continue

        layer = layout_layer_id(layout_id, shift=mods.shift_active)
        ch = vk_index.get((layer, key_id)) or vk_index.get((layout_id, key_id))
        if ch:
            out.append(ch)
    return "".join(out)


def decode_branches(
    events: list[dict[str, Any]],
    layout_ids: list[str] | None = None,
    *,
    state: dict | None = None,
    vk_index: dict[tuple[str, str], str] | None = None,
) -> dict[str, str]:
    if vk_index is None:
        vk_index, _ = resolve_decode_index(state=state)
    role_index = resolve_role_index(state=state)
    ids = layout_ids or list_layout_ids(state=state)
    return {
        lid: decode_events(events, lid, vk_index=vk_index, role_index=role_index, state=state)
        for lid in ids
    }


def events_from_key_ids(key_ids: list[str]) -> list[dict[str, str]]:
    return [{"key_id": kid, "action": "down"} for kid in key_ids]


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="VK decode via field compose (or JSON fallback)")
    p.add_argument("--layout", default=None)
    p.add_argument("--keys", nargs="*", default=[])
    p.add_argument("--json", type=Path, default=None)
    p.add_argument("--source", choices=("auto", "json"), default="auto")
    args = p.parse_args()

    state = None
    if args.source == "auto":
        from boot_core_ltm_v0 import default_core_ltm_dir, merge_core_ltm  # type: ignore

        core = default_core_ltm_dir()
        if (core / "pack.manifest.json").is_file():
            state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
            merge_core_ltm(state, core)
            ensure_vk_compose_index(state)

    if args.json:
        events = list(json.loads(args.json.read_text(encoding="utf-8")).get("events") or [])
    else:
        events = events_from_key_ids(list(args.keys))

    vk_index = _json_index() if args.source == "json" else None
    if args.layout:
        text = decode_events(events, args.layout, vk_index=vk_index, state=state)
        print(json.dumps({"layout_id": args.layout, "grapheme_string": text}, ensure_ascii=False))
    else:
        branches = decode_branches(events, vk_index=vk_index, state=state)
        _, src = resolve_decode_index(state=state) if vk_index is None else ("json", "json")
        print(json.dumps({"source": src, "branches": branches}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
