#!/usr/bin/env python3
"""Keyboard catalog: modifiers, actions, zones, shift layers (full device ontology v1)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_KEYS_PATH = REPO_ROOT / "design" / "keyboard-layouts" / "keyboard-keys.json"

SHIFT_KEYS = frozenset({"ShiftLeft", "ShiftRight"})
CAPS_LOCK_KEY = "CapsLock"
LAYER_BASE = "base"
LAYER_SHIFT = "shift"


@lru_cache(maxsize=1)
def load_keyboard_catalog() -> dict[str, Any]:
    return json.loads(_KEYS_PATH.read_text(encoding="utf-8"))


def device_concept_id() -> str:
    return str(load_keyboard_catalog().get("device_id") or "input.device.keyboard")


def modifier_key_ids() -> frozenset[str]:
    return frozenset(load_keyboard_catalog().get("modifiers") or {})


def modifier_concept(key_id: str) -> str | None:
    return (load_keyboard_catalog().get("modifiers") or {}).get(key_id)


def action_key_ids() -> frozenset[str]:
    cat = load_keyboard_catalog()
    keys: set[str] = set()
    keys.update((cat.get("actions") or {}).keys())
    keys.update((cat.get("navigation") or {}).keys())
    keys.update((cat.get("function") or {}).keys())
    return frozenset(keys)


def action_concept(key_id: str) -> str | None:
    cat = load_keyboard_catalog()
    for section in ("actions", "navigation", "function"):
        hit = (cat.get(section) or {}).get(key_id)
        if hit:
            return str(hit)
    return None


def zone_for_key(key_id: str) -> str | None:
    for zone_id, keys in (load_keyboard_catalog().get("zones") or {}).items():
        if key_id in keys:
            return str(zone_id)
    return None


def all_catalog_key_ids() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    cat = load_keyboard_catalog()

    def _add(keys: dict | list | frozenset) -> None:
        if isinstance(keys, dict):
            iterable = keys.keys()
        else:
            iterable = keys
        for kid in iterable:
            s = str(kid)
            if s and s not in seen:
                seen.add(s)
                out.append(s)

    for section in ("modifiers", "actions", "navigation", "function"):
        _add(cat.get(section) or {})
    for keys in (cat.get("zones") or {}).values():
        _add(keys)
    return out


def layout_layer_id(layout_id: str, *, shift: bool = False) -> str:
    return f"{layout_id}.shift" if shift else layout_id


def action_glyph(action_cid: str) -> str:
    """Lab-visible control glyphs for decode stream (not grapheme L0)."""
    table = {
        "action.enter": "\n",
        "action.tab": "\t",
        "action.backspace": "\b",
        "action.escape": "\u001b",
        "action.delete": "\u007f",
        "action.insert": "\u0090",
        "action.arrow_up": "\u2191",
        "action.arrow_down": "\u2193",
        "action.arrow_left": "\u2190",
        "action.arrow_right": "\u2192",
        "action.home": "\u21e4",
        "action.end": "\u21e5",
        "action.page_up": "\u21de",
        "action.page_down": "\u21df",
    }
    if action_cid.startswith("action.f") and action_cid[8:].isdigit():
        n = int(action_cid[8:])
        return chr(0xF000 + n) if 1 <= n <= 12 else ""
    return table.get(action_cid, "")
