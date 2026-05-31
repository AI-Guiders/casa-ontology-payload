#!/usr/bin/env python3
"""Boot linked RU + EN agent stores into one runtime field (cross-store hub)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.grapheme_ingest import L0_ID, merge_l0_lattices
from casa.prisms.memory.lexicon_usage_axes import attach_axes_to_state, axes_report, merge_locale_axes
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.lexicon_shard import is_l2_en_word_lattice, sharding_config
from casa.prisms.shared.store_boot import boot_store


def _copy_lattice(lat: dict) -> dict:
    return {
        **lat,
        "cells": [list(cell) for cell in (lat.get("cells") or [])],
    }


def merge_linked_states(
    ru_state: dict,
    en_state: dict,
    *,
    ru_dir: Path | None = None,
    en_dir: Path | None = None,
) -> dict[str, Any]:
    """Merge RU ltm boot + EN store lattices; preserve separate L2 namespaces."""
    base = ensure_prisms(copy.deepcopy(ru_state))
    en = ensure_prisms(en_state)
    ru_lattices = memory_lattices(base)
    en_lattices = memory_lattices(en)

    for lid, lat in en_lattices.items():
        if is_l2_en_word_lattice(lid):
            ru_lattices[lid] = _copy_lattice(lat)
        elif lid == "L1_syllable" and lid not in ru_lattices:
            ru_lattices[lid] = _copy_lattice(lat)

    en_l0 = en_lattices.get(L0_ID)
    if en_l0:
        ru_l0 = ru_lattices.get(L0_ID)
        if ru_l0:
            ru_lattices[L0_ID] = merge_l0_lattices(_copy_lattice(ru_l0), _copy_lattice(en_l0))
        else:
            ru_lattices[L0_ID] = _copy_lattice(en_l0)

    base["prisms"]["prism_memory"]["lattices"] = ru_lattices
    base.setdefault("sss", {})["lattices"] = ru_lattices

    ru_cfg = sharding_config(base)
    en_cfg = sharding_config(en)
    merged_index = dict(ru_cfg.get("word_index") or {})
    for word, shard in (en_cfg.get("word_index") or {}).items():
        if is_l2_en_word_lattice(str(shard)):
            merged_index[word] = shard
    ru_cfg["word_index"] = merged_index
    ru_cfg["en"] = dict(en_cfg.get("en") or {})
    if en_cfg.get("locale"):
        ru_cfg["en"]["source_locale"] = en_cfg["locale"]
    base["l2_sharding"] = ru_cfg

    linked: dict[str, str] = {}
    if ru_dir:
        linked["ru"] = str(ru_dir.resolve())
    if en_dir:
        linked["en"] = str(en_dir.resolve())
    base["linked_stores"] = linked
    base.setdefault("store", {})["boot_source"] = "linked_ru_en"
    base["field_version"] = max(
        int(base.get("field_version") or 0),
        int(en.get("field_version") or 0),
    )

    ru_axes = ru_state.get("lexicon_axes") or {}
    en_axes = en_state.get("lexicon_axes") or {}
    if ru_axes or en_axes:
        merged_axes = merge_locale_axes(ru_axes, en_axes)
        attach_axes_to_state(base, merged_axes)
        base["store"]["lexicon_axes_summary"] = {
            **axes_report(merged_axes),
            "schema": "lexicon_usage_axes",
            "locales": {
                "ru": len(ru_axes),
                "en": len(en_axes),
            },
        }

    return base


def boot_linked_stores(
    ru_dir: Path,
    en_dir: Path,
    *,
    ru_prefer_field_state: bool = False,
    en_prefer_field_state: bool = True,
    core_ltm_dir: Path | None = None,
    merge_vk: bool = True,
) -> dict[str, Any]:
    ru = boot_store(ru_dir, prefer_field_state=ru_prefer_field_state)
    en = boot_store(en_dir, prefer_field_state=en_prefer_field_state)
    state = merge_linked_states(
        ru["state"],
        en["state"],
        ru_dir=ru_dir,
        en_dir=en_dir,
    )
    vk_boot: dict | None = None
    if merge_vk:
        from casa.prisms.memory.boot_core_ltm import merge_core_ltm_stack

        vk_boot = merge_core_ltm_stack(
            state,
            include_alphabet=True,
            include_vk=True,
            vk_ltm=core_ltm_dir,
        )
    en_shards = sum(1 for k in memory_lattices(state) if is_l2_en_word_lattice(k))
    return {
        "ru_boot": {"source": ru.get("source"), "l2_shard_count": ru.get("l2_shard_count")},
        "en_boot": {"source": en.get("source"), "l2_shard_count": en_shards},
        "lattice_count": len(memory_lattices(state)),
        "field_version": state.get("field_version"),
        "vk_boot": vk_boot,
        "state": state,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Boot linked RU + EN stores")
    p.add_argument("--ru-store", type=Path, required=True)
    p.add_argument("--en-store", type=Path, required=True)
    p.add_argument("--ru-prefer-field-state", action="store_true")
    p.add_argument("--en-prefer-field-state", action="store_true", default=True)
    args = p.parse_args()

    boot = boot_linked_stores(
        args.ru_store,
        args.en_store,
        ru_prefer_field_state=args.ru_prefer_field_state,
        en_prefer_field_state=args.en_prefer_field_state,
    )
    out = {k: v for k, v in boot.items() if k != "state"}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
