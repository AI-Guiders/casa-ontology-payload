#!/usr/bin/env python3
"""Immutable RU (33 cyrl) + EN (26 latn) on separate L0 lattices — agent-core pack."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from casa.domain.prism_wire import prism_memory
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.memory.grapheme_ingest import (
    GRAPHEME_CYRL_PREFIX,
    GRAPHEME_LATN_PREFIX,
    L0_CYRL_ID,
    L0_GRAPHEME_IDS,
    L0_LATN_ID,
    ingest_graphemes_batch,
    l0_lattice_id,
    merge_l0_lattices,
)
from casa.prisms.shared.ltm_pack import lattice_subdir, write_ltm
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.stack import decode_lattice

Script = Literal["latn", "cyrl"]

RU_CYRL_ALPHABET_33: tuple[str, ...] = tuple(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)

EN_LATN_ALPHABET_26: tuple[str, ...] = tuple(chr(c) for c in range(ord("a"), ord("z") + 1))

ALPHABET_CORE_KIND = "core_ltm_alphabet"
DEFAULT_COPIES_CYRL = 6
DEFAULT_COPIES_LATN = 5


def ru_cyrl_alphabet() -> list[str]:
    if len(RU_CYRL_ALPHABET_33) != 33:
        raise ValueError(f"RU_CYRL_ALPHABET_33 must be 33 chars, got {len(RU_CYRL_ALPHABET_33)}")
    return list(RU_CYRL_ALPHABET_33)


def en_latn_alphabet() -> list[str]:
    return list(EN_LATN_ALPHABET_26)


def imprint_alphabet_on_l0(
    state: dict,
    *,
    include_ru: bool = True,
    include_en: bool = True,
    copies_cyrl: int = DEFAULT_COPIES_CYRL,
    copies_latn: int = DEFAULT_COPIES_LATN,
) -> dict[str, Any]:
    """Listen immutable alphabets onto script-specific L0 lattices."""
    state = ensure_prisms(state)
    rep: dict[str, Any] = {"lattices": list(L0_GRAPHEME_IDS)}
    if include_en:
        rep["latn"] = ingest_graphemes_batch(state, en_latn_alphabet(), "latn", copies=copies_latn)
    if include_ru:
        rep["cyrl"] = ingest_graphemes_batch(state, ru_cyrl_alphabet(), "cyrl", copies=copies_cyrl)
    lattices = memory_lattices(state)
    for lid in L0_GRAPHEME_IDS:
        lat = lattices.get(lid) or {}
        lat["immutable"] = True
        lat["kind"] = ALPHABET_CORE_KIND
        lattices[lid] = lat
    lat_cyrl = lattices.get(L0_CYRL_ID) or {}
    lat_cyrl["alphabet_ru_n"] = 33
    lat_latn = lattices.get(L0_LATN_ID) or {}
    lat_latn["alphabet_en_n"] = 26
    prism_memory(state)["lattices"] = lattices
    rep["verify"] = verify_alphabet_on_l0(state)
    return rep


def verify_alphabet_on_l0(state: dict, *, min_votes: int = 1) -> dict[str, Any]:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    cyrl_lat = lattices.get(L0_CYRL_ID) or {}
    latn_lat = lattices.get(L0_LATN_ID) or {}
    dec_cyrl = decode_lattice(cyrl_lat, min_votes=min_votes)
    dec_latn = decode_lattice(latn_lat, min_votes=min_votes)
    cyrl_on = {
        str(c.get("concept_id", ""))[len(GRAPHEME_CYRL_PREFIX) :]
        for c in dec_cyrl.get("concepts") or []
        if str(c.get("concept_id", "")).startswith(GRAPHEME_CYRL_PREFIX)
    }
    latn_on = {
        str(c.get("concept_id", ""))[len(GRAPHEME_LATN_PREFIX) :]
        for c in dec_latn.get("concepts") or []
        if str(c.get("concept_id", "")).startswith(GRAPHEME_LATN_PREFIX)
    }
    ru_expected = set(ru_cyrl_alphabet())
    en_expected = set(en_latn_alphabet())
    return {
        "ru_on_field": len(cyrl_on),
        "ru_lattice": L0_CYRL_ID,
        "ru_expected": len(ru_expected),
        "ru_missing": sorted(ru_expected - cyrl_on),
        "en_on_field": len(latn_on),
        "en_lattice": L0_LATN_ID,
        "en_expected": len(en_expected),
        "en_missing": sorted(en_expected - latn_on),
        "pass": not (ru_expected - cyrl_on) and not (en_expected - latn_on),
    }


def export_alphabet_core_ltm(out_dir: Path, *, copies_cyrl: int = DEFAULT_COPIES_CYRL, copies_latn: int = DEFAULT_COPIES_LATN) -> dict[str, Any]:
    """Build immutable cyrl+latn L0 pack under <out_dir>/ltm/."""
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    imprint_rep = imprint_alphabet_on_l0(
        state,
        copies_cyrl=copies_cyrl,
        copies_latn=copies_latn,
    )
    lattices = memory_lattices(state)
    ltm_dir = out_dir / "ltm"
    rows: dict[str, dict] = {}
    total_raw = 0
    total_file = 0
    for lid in L0_GRAPHEME_IDS:
        lat = lattices[lid]
        sub = lattice_subdir(lid)
        path = ltm_dir / sub / f"{lid}.ltm"
        info = write_ltm(path, lat, compress=False)
        meta = {k: v for k, v in lat.items() if k not in ("width", "height", "cells")}
        rows[lid] = {**info, "meta": meta}
        total_raw += int(info["raw_bytes"])
        total_file += int(info["file_bytes"])
    manifest = {
        "schema_version": 1,
        "format": "ltm-pack",
        "kind": ALPHABET_CORE_KIND,
        "immutable": True,
        "decode_mode": "digest",
        "field_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lattices": rows,
        "totals": {
            "lattice_count": len(rows),
            "ru_graphemes": 33,
            "en_graphemes": 26,
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
        "imprint": imprint_rep,
        "verify": imprint_rep.get("verify"),
    }
    ltm_dir.mkdir(parents=True, exist_ok=True)
    (ltm_dir / "pack.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def merge_alphabet_l0_from_ltm(state: dict, ltm_dir: Path, *, manifest: dict | None = None) -> dict[str, Any]:
    """Import alphabet L0 lattices; migrate legacy monolith if present."""
    from casa.prisms.shared.import_ltm_pack import import_pack

    state = ensure_prisms(state)
    ltm_dir = ltm_dir.resolve()
    imp = import_pack(state, ltm_dir, manifest=manifest)
    return {"import": imp, "verify": verify_alphabet_on_l0(state)}


def merge_alphabet_overlay_lattice(
    state: dict,
    script: Script,
    overlay_lat: dict,
) -> None:
    """Merge VK/legacy overlay into one script lattice."""
    lid = l0_lattice_id(script)
    lattices = memory_lattices(state)
    before = lattices.get(lid)
    if before and overlay_lat:
        lattices[lid] = merge_l0_lattices(before, overlay_lat)
        prism_memory(state)["lattices"] = lattices
        state.setdefault("sss", {})["lattices"] = lattices
